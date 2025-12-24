import { useState } from "react";
import PropTypes from "prop-types";
import "./DiagramDisplay.css";

export const DiagramDisplay = ({ diagrams }) => {
  const [imageErrors, setImageErrors] = useState({});

  if (!diagrams || diagrams.length === 0) {
    return null;
  }

  const handleImageError = (index) => {
    setImageErrors((prev) => ({ ...prev, [index]: true }));
    console.error(
      `Failed to load diagram image at index ${index}`,
      diagrams[index]
    );
    console.error(`Image URL:`, diagrams[index].url);
    console.error(`URL length:`, diagrams[index].url?.length);
    console.error(`URL preview:`, diagrams[index].url?.substring(0, 100));
  };

  const handleImageLoad = (index) => {
    console.log(`Successfully loaded diagram image at index ${index}`);
  };

  return (
    <div className="diagrams-container">
      <h3>📊 Generated Diagrams</h3>
      <p className="diagrams-description">
        Visual representations auto-generated from your project plan
      </p>

      <div className="diagrams-grid">
        {diagrams.map((diagram, index) => (
          <div key={index} className="diagram-card">
            <div className="diagram-header">
              <h4>{diagram.title}</h4>
              <span className="diagram-type">{diagram.type}</span>
            </div>

            <p className="diagram-description">{diagram.description}</p>

            <div className="diagram-image-container">
              {imageErrors[index] ? (
                <div style={{ color: "red", padding: "20px" }}>
                  ⚠️ Failed to load diagram image. Check the source code below
                  for details.
                </div>
              ) : (
                <img
                  src={diagram.url}
                  alt={diagram.title}
                  className="diagram-image"
                  onError={() => handleImageError(index)}
                  onLoad={() => handleImageLoad(index)}
                />
              )}
            </div>

            <details className="diagram-source">
              <summary>View Source Code</summary>
              <pre className="diagram-source-code">
                <code>{diagram.source_code}</code>
              </pre>
            </details>
          </div>
        ))}
      </div>
    </div>
  );
};

DiagramDisplay.propTypes = {
  diagrams: PropTypes.arrayOf(
    PropTypes.shape({
      type: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      url: PropTypes.string.isRequired,
      source_code: PropTypes.string.isRequired,
    })
  ).isRequired,
};
