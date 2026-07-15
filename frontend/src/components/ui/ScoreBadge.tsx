/**
 * The Fit Dial — the product's signature instrument readout (design brief §4.1).
 * A 270° arc whose stroke follows the score semantic, number set inside in
 * JetBrains Mono. Same component from the 28px table cell to the 72px
 * detail-panel hero. Score is never a plain number or a progress bar.
 */
export default function ScoreBadge({ score, size = 28 }: { score: number | null | undefined; size?: number }) {
  const rounded = score == null ? null : Math.round(score);
  const color =
    rounded == null
      ? "var(--border-strong)"
      : rounded >= 75
      ? "var(--score-high)"
      : rounded >= 50
      ? "var(--score-mid)"
      : "var(--score-low)";

  const stroke = size >= 48 ? 3.5 : 2.5;
  const r = (size - stroke) / 2;
  const c = size / 2;
  const sweep = 0.75; // 270° of the circle
  const circumference = 2 * Math.PI * r;
  const track = circumference * sweep;
  const value = rounded == null ? 0 : track * (rounded / 100);

  return (
    <span
      role="img"
      aria-label={rounded == null ? "not scored" : `fit score ${rounded} of 100`}
      style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", position: "relative", width: size, height: size, flexShrink: 0 }}
    >
      {/* rotate so the 270° sweep opens at the bottom, gauge-style */}
      <svg width={size} height={size} style={{ transform: "rotate(135deg)" }} aria-hidden>
        <circle
          cx={c}
          cy={c}
          r={r}
          fill="none"
          stroke="var(--border)"
          strokeWidth={stroke}
          strokeLinecap="round"
          strokeDasharray={`${track} ${circumference}`}
        />
        {rounded != null && (
          <circle
            cx={c}
            cy={c}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={`${value} ${circumference}`}
          />
        )}
      </svg>
      <span
        className="data"
        style={{
          position: "absolute",
          fontSize: size >= 48 ? size * 0.28 : 10,
          color: rounded == null ? "var(--ink-tertiary)" : color,
          lineHeight: 1,
        }}
      >
        {rounded == null ? "" : rounded}
      </span>
    </span>
  );
}
