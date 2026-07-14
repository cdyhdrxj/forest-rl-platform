import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from "recharts"
import { Theme, card, secLabel } from "../constants/colors"

const METRICS_COLORS = {
  metric_M_idleness: "#f59e0b",
  metric_M_damage:   "#ef4444",
  metric_M_move:     "#8b5cf6",
  metric_Z:          "#007bff",
}

const METRICS_LABELS = {
  metric_M_idleness: "M_idleness",
  metric_M_damage:   "M_damage",
  metric_M_move:     "M_move",
  metric_Z:          "Z (цел. функция)",
}

const xFmt = v => v >= 1000 ? `${(v / 1000).toFixed(0)}k` : String(v)

export function ValChartsPanel({ valChartData }) {
  if (!valChartData || valChartData.length === 0) return null

  return (
    <>
      {/* Chart 1: M_idleness, M_damage, M_move, Z */}
      <div style={{ ...card, padding: 16 }}>
        <div style={secLabel}>Метрики валидации</div>
        <ResponsiveContainer width="100%" height={200}>
          <LineChart data={valChartData} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
            <XAxis
              dataKey="step"
              tickFormatter={xFmt}
              tick={{ fontSize: 10, fill: Theme.textMuted }}
              label={{ value: "Шаг обучения", position: "insideBottom", offset: -10, fontSize: 10, fill: Theme.textSecond }}
            />
            <YAxis width={40} tick={{ fontSize: 10, fill: Theme.textMuted }} />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}`, boxShadow: Theme.shadow, background: Theme.surface }}
              labelFormatter={v => `Шаг: ${v.toLocaleString()}`}
              formatter={(v, name) => [typeof v === "number" ? v.toFixed(4) : v, METRICS_LABELS[name] ?? name]}
            />
            <Legend iconSize={10} wrapperStyle={{ fontSize: 11, paddingTop: 4 }} formatter={n => METRICS_LABELS[n] ?? n} />
            {Object.entries(METRICS_COLORS).map(([key, color]) => (
              <Line key={key} type="monotone" dataKey={key} stroke={color} dot={{ r: 3 }} strokeWidth={1.5} name={key} />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </div>

      {/* Chart 2: catch_rate */}
      <div style={{ ...card, padding: 16 }}>
        <div style={secLabel}>Catch rate (валидация)</div>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={valChartData} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
            <XAxis
              dataKey="step"
              tickFormatter={xFmt}
              tick={{ fontSize: 10, fill: Theme.textMuted }}
              label={{ value: "Шаг обучения", position: "insideBottom", offset: -10, fontSize: 10, fill: Theme.textSecond }}
            />
            <YAxis width={40} tick={{ fontSize: 10, fill: Theme.textMuted }} domain={[0, 1]}
              tickFormatter={v => `${(v * 100).toFixed(0)}%`} />
            <Tooltip
              contentStyle={{ fontSize: 11, borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}`, boxShadow: Theme.shadow, background: Theme.surface }}
              labelFormatter={v => `Шаг: ${v.toLocaleString()}`}
              formatter={v => [`${(v * 100).toFixed(1)}%`, "Catch rate"]}
            />
            <Line type="monotone" dataKey="catch_rate" stroke={Theme.green} dot={{ r: 3 }} strokeWidth={1.5} name="catch_rate" />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </>
  )
}
