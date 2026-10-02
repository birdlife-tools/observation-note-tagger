import { ReactNode } from "react";
import { Page } from "../App";

interface LayoutProps {
  children: ReactNode;
  currentPage: Page;
  onNavigate: (page: Page) => void;
}

export function Layout({ children, currentPage, onNavigate }: LayoutProps) {
  return (
    <div className="min-h-screen font-sans">
      <header className="bg-birdlife-card border-b border-birdlife-border">
        <div className="max-w-6xl mx-auto px-4 sm:px-6">
          <div className="flex justify-between items-center h-14">
            <div className="flex items-center gap-2">
              <span className="text-birdlife-primary font-semibold">ONT</span>
              <span className="text-birdlife-muted text-sm">
                Observation Note Tagger
              </span>
            </div>
            <nav className="flex gap-6 text-sm">
              <button
                onClick={() => onNavigate("review")}
                className={`pb-0.5 ${
                  currentPage === "review"
                    ? "text-birdlife-primary font-medium border-b-2 border-birdlife-primary"
                    : "text-birdlife-muted hover:text-birdlife-text"
                }`}
              >
                Review Queue
              </button>
              <button
                onClick={() => onNavigate("stats")}
                className={`pb-0.5 ${
                  currentPage === "stats"
                    ? "text-birdlife-primary font-medium border-b-2 border-birdlife-primary"
                    : "text-birdlife-muted hover:text-birdlife-text"
                }`}
              >
                Statistics
              </button>
            </nav>
          </div>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 sm:px-6 py-6">{children}</main>
    </div>
  );
}
