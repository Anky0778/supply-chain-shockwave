export default function Sparkline({
  values,
  width = 96,
  height = 28,
}: {
  values: number[];
  width?: number;
  height?: number;
}) {
  if (values.length < 2) return null;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const pts = values.map((v, i) => [
    (i / (values.length - 1)) * width,
    height - 2 - ((v - min) / span) * (height - 4),
  ]);
  const last = pts[pts.length - 1];
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Five-year price trend">
      <polyline
        points={pts.map((p) => p.join(",")).join(" ")}
        fill="none"
        stroke="#1c1b19"
        strokeWidth="1.25"
      />
      <circle cx={last[0]} cy={last[1]} r="2" fill="#1c1b19" />
    </svg>
  );
}