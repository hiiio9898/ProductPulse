/** 轻量级价格走势 Sparkline（内联 SVG，无第三方依赖）。 */
export default function Sparkline({
  data,
  width = 120,
  height = 32,
  color = "#1890ff",
}: {
  data: (number | null)[];
  width?: number;
  height?: number;
  color?: string;
}) {
  const points = data.filter((v): v is number => v !== null && v > 0);
  if (points.length < 2) {
    return <span style={{ color: "#bfbfbf", fontSize: 12 }}>--</span>;
  }
  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const stepX = width / (points.length - 1);
  const coords = points.map((v, i) => {
    const x = i * stepX;
    const y = height - ((v - min) / range) * (height - 4) - 2;
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });
  const path = `M ${coords.join(" L ")}`;
  return (
    <svg width={width} height={height} style={{ display: "inline-block", verticalAlign: "middle" }}>
      <path d={path} fill="none" stroke={color} strokeWidth={1.5} />
      <circle cx={(points.length - 1) * stepX} cy={height - ((points[points.length - 1] - min) / range) * (height - 4) - 2} r={2} fill={color} />
    </svg>
  );
}
