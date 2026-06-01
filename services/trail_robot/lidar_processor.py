import numpy as np


class LidarProcessor:
    """
    Универсальный обработчик лидара: разбивает на сектора по 5° и берёт минимум.
    
    Лидар в платформе: 2D LaserScan, 180°, 180 точек (1 точка/градус).
    Каждый сектор = 5° = 5 точек, берётся минимум.
    """
    
    def __init__(self, degrees_per_sector=5, max_range=5.0):
        """
        Args:
            degrees_per_sector: градусов на один сектор (по умолчанию 5°)
            max_range: максимальная дальность лидара (м)
        """
        self.degrees_per_sector = degrees_per_sector
        self.max_range = max_range
        
        # Количество секторов = 180° / градусов_на_сектор
        self.n_sectors = 180 // degrees_per_sector  # 36 секторов по 5°
        self.points_per_sector = degrees_per_sector  # 5 точек в секторе (1 точка/градус)
    
    def process(self, ranges):
        """
        Принимает массив расстояний лидара (любой длины).
        Разбивает на сектора по N градусов (точек) и берёт минимум в каждом.
        
        Args:
            ranges: массив расстояний (list или np.array)
        
        Returns:
            sectors: np.array минимальных расстояний в каждом секторе
        """
        if ranges is None or len(ranges) == 0:
            return np.full(self.n_sectors, self.max_range, dtype=np.float32)
        
        # Чистим данные
        ranges = np.array(ranges, dtype=np.float32)
        ranges = np.clip(ranges, 0.0, self.max_range)
        ranges = np.nan_to_num(ranges, nan=self.max_range, posinf=self.max_range, neginf=0.0)
        
        # Определяем реальное количество точек и секторов
        n_points = len(ranges)
        n_sectors = max(1, n_points // self.points_per_sector)  # сколько секторов влезет
        
        # Обрезаем до целого числа секторов
        usable_points = n_sectors * self.points_per_sector
        ranges = ranges[:usable_points]
        
        # Разбиваем на сектора и берём минимум
        sectors = ranges.reshape(n_sectors, self.points_per_sector)
        sector_mins = np.min(sectors, axis=1).astype(np.float32)
        
        # Дополняем до стандартного размера если нужно
        if len(sector_mins) < self.n_sectors:
            padded = np.full(self.n_sectors, self.max_range, dtype=np.float32)
            padded[:len(sector_mins)] = sector_mins
            return padded
        
        return sector_mins[:self.n_sectors]
    
    def normalize(self, sectors):
        """Нормализация секторов в [0, 1]"""
        return np.clip(sectors / self.max_range, 0.0, 1.0).astype(np.float32)
    
    def get_min(self, sectors):
        """Минимальное расстояние по всем секторам"""
        return float(np.min(sectors))
    
    def get_front(self, sectors):
        """Минимальное расстояние в передних секторах (центральные 2/3)"""
        n = len(sectors)
        start = n // 6      # ~30° от левого края
        end = 5 * n // 6    # ~30° от правого края
        return float(np.min(sectors[start:end]))