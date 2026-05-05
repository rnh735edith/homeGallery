export default function QualityBadge({ score, className = "" }) {
  if (score === null || score === undefined) return null;

  let qualityClass = "quality-low";
  if (score >= 80) {
    qualityClass = "quality-high";
  } else if (score >= 50) {
    qualityClass = "quality-medium";
  }

  return (
    <span className={`quality-badge ${qualityClass} ${className}`}>
      {score}
    </span>
  );
}
