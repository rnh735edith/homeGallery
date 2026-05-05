export default function AnalysisPanel({ metadata }) {
  if (!metadata) return null;

  const { quality_score, sharpness, noise_level, composition, colors } =
    metadata;

  const getQualityClass = (score) => {
    if (score >= 80) return "high";
    if (score >= 50) return "medium";
    return "low";
  };

  return (
    <div className="analysis-panel">
      <h3>Analysis Results</h3>

      {quality_score !== null && quality_score !== undefined && (
        <div className="analysis-metric">
          <label>Quality</label>
          <div className="progress-bar">
            <div
              className={`progress-fill ${getQualityClass(quality_score)}`}
              style={{ width: `${quality_score}%` }}
            />
          </div>
          <span className="metric-value">{quality_score}</span>
        </div>
      )}

      {sharpness !== null && sharpness !== undefined && (
        <div className="analysis-metric">
          <label>Sharpness</label>
          <span className="metric-value">{sharpness}</span>
        </div>
      )}

      {noise_level !== null && noise_level !== undefined && (
        <div className="analysis-metric">
          <label>Noise Level</label>
          <span className="metric-value">{noise_level}</span>
        </div>
      )}

      {composition && (
        <div className="composition-scores">
          <h4>Composition</h4>
          {composition.rule_of_thirds !== null &&
            composition.rule_of_thirds !== undefined && (
              <div className="composition-score">
                <span className="score-label">Rule of Thirds</span>
                <span className="score-value">
                  {composition.rule_of_thirds}
                </span>
              </div>
            )}
          {composition.symmetry !== null &&
            composition.symmetry !== undefined && (
              <div className="composition-score">
                <span className="score-label">Symmetry</span>
                <span className="score-value">{composition.symmetry}</span>
              </div>
            )}
          {composition.leading_lines !== null &&
            composition.leading_lines !== undefined && (
              <div className="composition-score">
                <span className="score-label">Leading Lines</span>
                <span className="score-value">{composition.leading_lines}</span>
              </div>
            )}
        </div>
      )}

      {colors && colors.length > 0 && (
        <div className="analysis-metric">
          <label>Color Palette</label>
          <div className="color-palette">
            {colors.map((color, index) => (
              <div
                key={index}
                className="color-swatch"
                style={{ backgroundColor: color }}
                title={color}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
