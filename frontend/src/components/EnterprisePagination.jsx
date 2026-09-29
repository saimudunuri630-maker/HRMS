import React from "react";
import "../styles/Modules.css";

export default function EnterprisePagination({
  currentPage,
  totalPages,
  totalItems,
  pageSize = 10,
  itemLabel = "records",
  onPageChange,
  standalone = false,
}) {
  // If no items or only 1 page, hide pagination per specifications
  if (!totalItems || totalItems <= pageSize || totalPages <= 1) {
    return null;
  }

  const startItem = (currentPage - 1) * pageSize + 1;
  const endItem = Math.min(currentPage * pageSize, totalItems);

  // Calculate clean page numbers window
  const getPageNumbers = () => {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => i + 1);
    }
    if (currentPage <= 4) {
      return [1, 2, 3, 4, 5, "...", totalPages];
    }
    if (currentPage >= totalPages - 3) {
      return [1, "...", totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages];
    }
    return [1, "...", currentPage - 1, currentPage, currentPage + 1, "...", totalPages];
  };

  const pages = getPageNumbers();

  return (
    <div className={`module-pagination-container ${standalone ? "module-pagination-standalone" : ""}`}>
      <div className="module-pagination-info">
        Showing {startItem}–{endItem} of {totalItems} {itemLabel}
      </div>
      <div className="module-pagination-controls">
        <button
          type="button"
          className="module-page-btn"
          onClick={() => onPageChange(currentPage - 1)}
          disabled={currentPage <= 1}
          aria-label="Previous page"
        >
          Previous
        </button>
        {pages.map((p, idx) =>
          p === "..." ? (
            <span key={`ellipsis-${idx}`} className="module-page-ellipsis" aria-hidden="true">
              …
            </span>
          ) : (
            <button
              key={p}
              type="button"
              className={`module-page-btn ${p === currentPage ? "active" : ""}`}
              onClick={() => onPageChange(p)}
              aria-current={p === currentPage ? "page" : undefined}
            >
              {p}
            </button>
          )
        )}
        <button
          type="button"
          className="module-page-btn"
          onClick={() => onPageChange(currentPage + 1)}
          disabled={currentPage >= totalPages}
          aria-label="Next page"
        >
          Next
        </button>
      </div>
    </div>
  );
}
