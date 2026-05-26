import React from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SummaryDisplay } from "./summary-display";

describe("SummaryDisplay", () => {
  describe("completed status", () => {
    it("displays summary text when language matches preference", () => {
      render(
        <SummaryDisplay
          status="completed"
          text="This is a summary."
          summaryLanguage="en"
          preferredLanguage="en"
        />
      );

      expect(screen.getByText("This is a summary.")).toBeInTheDocument();
      expect(screen.queryByText(/preferred language not available/)).not.toBeInTheDocument();
    });

    it("displays summary with language mismatch notice when languages differ", () => {
      render(
        <SummaryDisplay
          status="completed"
          text="This is a summary in English."
          summaryLanguage="en"
          preferredLanguage="ja"
        />
      );

      expect(screen.getByText("This is a summary in English.")).toBeInTheDocument();
      expect(
        screen.getByText("Shown in English — preferred language not available")
      ).toBeInTheDocument();
    });

    it("does not show notice when summaryLanguage is not provided", () => {
      render(
        <SummaryDisplay
          status="completed"
          text="Summary text"
          preferredLanguage="ja"
        />
      );

      expect(screen.getByText("Summary text")).toBeInTheDocument();
      expect(screen.queryByText(/preferred language not available/)).not.toBeInTheDocument();
    });

    it("does not show notice when preferredLanguage is not provided", () => {
      render(
        <SummaryDisplay
          status="completed"
          text="Summary text"
          summaryLanguage="en"
        />
      );

      expect(screen.getByText("Summary text")).toBeInTheDocument();
      expect(screen.queryByText(/preferred language not available/)).not.toBeInTheDocument();
    });

    it("shows correct language name in notice for non-English fallback", () => {
      render(
        <SummaryDisplay
          status="completed"
          text="Resumen en español"
          summaryLanguage="es"
          preferredLanguage="ja"
        />
      );

      expect(
        screen.getByText("Shown in Spanish — preferred language not available")
      ).toBeInTheDocument();
    });
  });

  describe("pending status", () => {
    it("shows generating message", () => {
      render(
        <SummaryDisplay
          status="pending"
          text={null}
          summaryLanguage="en"
          preferredLanguage="ja"
        />
      );

      expect(screen.getByText("Summary is being generated...")).toBeInTheDocument();
      expect(screen.queryByText(/preferred language not available/)).not.toBeInTheDocument();
    });
  });

  describe("failed status", () => {
    it("shows error message for failed status", () => {
      render(
        <SummaryDisplay
          status="failed"
          text={null}
        />
      );

      expect(screen.getByText("Summary could not be generated.")).toBeInTheDocument();
    });

    it("shows error message for permanently_failed status", () => {
      render(
        <SummaryDisplay
          status="permanently_failed"
          text={null}
        />
      );

      expect(screen.getByText("Summary could not be generated.")).toBeInTheDocument();
    });
  });

  describe("not_applicable status", () => {
    it("shows no summary available message", () => {
      render(
        <SummaryDisplay
          status="not_applicable"
          text={null}
        />
      );

      expect(screen.getByText("No summary available.")).toBeInTheDocument();
    });
  });
});
