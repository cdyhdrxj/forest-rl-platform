import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts"
import { Theme, card, secLabel } from "../constants/colors"

export function RewardChart({ chartData }) {
  return (
    <div style={{ ...card, padding: 16 }}>
      <div style={secLabel}>Динамика вознаграждения</div>
      <ResponsiveContainer width="100%" height={220}>
        <LineChart data={chartData} margin={{ top: 4, right: 8, left: 0, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f2f5" />
          <XAxis dataKey="i" tick={{ fontSize: 10, fill: Theme.textMuted }}
            label={{ value: "Эпизод", position: "insideBottom", offset: -10, fontSize: 10, fill: Theme.textSecond }} />
          <YAxis width={40} tick={{ fontSize: 10, fill: Theme.textMuted }}
            label={{ value: "Награда", angle: -90, position: "insideLeft", fontSize: 10, fill: Theme.textSecond }} />
          <Tooltip
            contentStyle={{ fontSize: 11, borderRadius: Theme.radiusSm, border: `1px solid ${Theme.border}`, boxShadow: Theme.shadow, background: Theme.surface }}
            labelStyle={{ color: Theme.textSecond }}
          />
          <Line type="monotone" dataKey="r" stroke={Theme.accent} dot={false} strokeWidth={1.5} name="Награда" />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}