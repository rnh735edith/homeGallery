import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import QualityBadge from "../QualityBadge";

describe("QualityBadge", () => {
  it("renders with quality score 85 as green (high quality)", () => {
    render(<QualityBadge score={85} />);

    const badge = screen.getByText("85");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("quality-badge", "quality-high");
  });

  it("renders with quality score 65 as yellow/orange (medium quality)", () => {
    render(<QualityBadge score={65} />);

    const badge = screen.getByText("65");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("quality-badge", "quality-medium");
  });

  it("renders with quality score 30 as red/gray (low quality)", () => {
    render(<QualityBadge score={30} />);

    const badge = screen.getByText("30");
    expect(badge).toBeInTheDocument();
    expect(badge).toHaveClass("quality-badge", "quality-low");
  });

  it("renders with score 100 as high quality", () => {
    render(<QualityBadge score={100} />);

    const badge = screen.getByText("100");
    expect(badge).toHaveClass("quality-high");
  });

  it("renders with score 0 as low quality", () => {
    render(<QualityBadge score={0} />);

    const badge = screen.getByText("0");
    expect(badge).toHaveClass("quality-low");
  });

  it("renders with custom className when provided", () => {
    render(<QualityBadge score={85} className="extra-class" />);

    const badge = screen.getByText("85");
    expect(badge).toHaveClass("quality-badge", "quality-high", "extra-class");
  });

  it("renders nothing when score is null", () => {
    render(<QualityBadge score={null} />);

    const badge = document.querySelector(".quality-badge");
    expect(badge).not.toBeInTheDocument();
  });

  it("renders nothing when score is undefined", () => {
    render(<QualityBadge score={undefined} />);

    const badge = document.querySelector(".quality-badge");
    expect(badge).not.toBeInTheDocument();
  });
});
