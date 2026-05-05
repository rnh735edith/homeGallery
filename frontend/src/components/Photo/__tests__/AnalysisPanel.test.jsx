import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import AnalysisPanel from "../AnalysisPanel";

describe("AnalysisPanel", () => {
  const mockMetadata = {
    quality_score: 85,
    sharpness: 0.75,
    noise_level: 0.2,
    composition: {
      rule_of_thirds: 0.8,
      symmetry: 0.6,
      leading_lines: 0.4,
    },
    colors: ["#ff0000", "#00ff00", "#0000ff"],
  };

  it("renders analysis panel with quality score progress bar", () => {
    render(<AnalysisPanel metadata={mockMetadata} />);

    expect(screen.getByText("Analysis Results")).toBeInTheDocument();
    expect(screen.getByText("Quality")).toBeInTheDocument();
    const progressBar = document.querySelector(
      ".analysis-metric .progress-fill",
    );
    expect(progressBar).toBeInTheDocument();
    expect(progressBar.style.width).toBe("85%");
  });

  it("renders sharpness metric", () => {
    render(<AnalysisPanel metadata={mockMetadata} />);

    expect(screen.getByText("Sharpness")).toBeInTheDocument();
    expect(screen.getByText("0.75")).toBeInTheDocument();
  });

  it("renders noise level metric", () => {
    render(<AnalysisPanel metadata={mockMetadata} />);

    expect(screen.getByText("Noise Level")).toBeInTheDocument();
    expect(screen.getByText("0.2")).toBeInTheDocument();
  });

  it("renders composition scores", () => {
    render(<AnalysisPanel metadata={mockMetadata} />);

    expect(screen.getByText("Rule of Thirds")).toBeInTheDocument();
    expect(screen.getByText("Symmetry")).toBeInTheDocument();
    expect(screen.getByText("Leading Lines")).toBeInTheDocument();
  });

  it("renders color palette with swatches", () => {
    render(<AnalysisPanel metadata={mockMetadata} />);

    const swatches = document.querySelectorAll(".color-swatch");
    expect(swatches).toHaveLength(3);
    expect(swatches[0].style.backgroundColor).toBe("rgb(255, 0, 0)");
  });

  it("renders nothing when metadata is null", () => {
    render(<AnalysisPanel metadata={null} />);

    expect(screen.queryByText("Analysis Results")).not.toBeInTheDocument();
  });

  it("renders nothing when metadata is undefined", () => {
    render(<AnalysisPanel metadata={undefined} />);

    expect(screen.queryByText("Analysis Results")).not.toBeInTheDocument();
  });

  it("applies correct color class based on quality score", () => {
    const lowQualityMetadata = { ...mockMetadata, quality_score: 30 };
    const { rerender } = render(
      <AnalysisPanel metadata={lowQualityMetadata} />,
    );

    let progressFill = document.querySelector(".progress-fill");
    expect(progressFill).toHaveClass("low");

    const highQualityMetadata = { ...mockMetadata, quality_score: 85 };
    rerender(<AnalysisPanel metadata={highQualityMetadata} />);

    progressFill = document.querySelector(".progress-fill");
    expect(progressFill).toHaveClass("high");
  });
});
