import { ReactNode } from "react";
import { X } from "lucide-react";

interface ModalProps {
  title: string;
  subtitle?: string;
  onClose: () => void;
  width?: number;
  children: ReactNode;
  footer?: ReactNode;
}

export default function Modal({ title, subtitle, onClose, width = 520, children, footer }: ModalProps) {
  return (
    <div
      style={{ position: "fixed", inset: 0, background: "rgba(20,25,43,0.35)", zIndex: 50 }}
      onClick={onClose}
    >
      <div
        className="card"
        style={{
          position: "fixed",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          width,
          maxHeight: "90vh",
          overflowY: "auto",
          boxShadow: "var(--shadow-float)",
          zIndex: 51,
        }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", position: "relative" }}>
          <div className="text-16 fw-600 c-primary">{title}</div>
          {subtitle && (
            <div className="text-12 c-faint" style={{ marginTop: 4 }}>
              {subtitle}
            </div>
          )}
          <button
            onClick={onClose}
            className="btn-ghost"
            style={{ position: "absolute", top: 16, right: 20, padding: 4 }}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>
        <div style={{ padding: 24 }}>{children}</div>
        {footer && (
          <div
            style={{
              padding: "16px 24px",
              borderTop: "1px solid var(--border)",
              display: "flex",
              justifyContent: "space-between",
            }}
          >
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}
