import roslibpy
import urllib.parse
import time

class RosApiConnection:
    _instance = None
    
    def __new__(cls, ros_url: str = "ws://localhost:9090"):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, ros_url: str = "ws://localhost:9090"):
        if self._initialized:
            return

        parsed = urllib.parse.urlparse(ros_url)

        host = parsed.hostname or "localhost"
        port = parsed.port or 9090

        self.connected = False
        self.client = None

        try:
            self.client = roslibpy.Ros(
                host=host,
                port=port
            )

            self.client.run()

            timeout = 5
            start = time.time()

            while time.time() - start < timeout:
                if self.client.is_connected:
                    self.connected = True
                    break

                time.sleep(0.1)

            if self.connected:
                print(f"ROS connected: {host}:{port}")
            else:
                print("ROS connection timeout")

        except Exception as e:
            print(f"ROS connection error: {e}")

        self._initialized = True
    
    def create_topic(self, name, msg_type):
        return roslibpy.Topic(self.client, name, msg_type)
    
    def call_service(self, name, service_type, request):
        service = roslibpy.Service(self.client, name, service_type)
        return service.call(request)

    def call_service_dict(self, name: str, service_type: str, request_dict: dict):
        service = roslibpy.Service(self.client, name, service_type)
        return service.call(request_dict)
    
    def disconnect(self):
        self.client.terminate()


ros = RosApiConnection("ws://ros2:9090")