import Modal from "./Modal";
import Button from "./Button";

interface ConfirmDialogProps {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  loading?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}

/** Generic destructive-action confirmation — used for deleting opportunities
 * and applications so a stray click can never lose data silently. */
export default function ConfirmDialog({
  title,
  message,
  confirmLabel = "Delete",
  danger = true,
  loading = false,
  onConfirm,
  onClose,
}: ConfirmDialogProps) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      width={400}
      footer={
        <>
          <Button variant="secondary" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button variant={danger ? "danger" : "primary"} size="sm" loading={loading} onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-13 c-secondary" style={{ lineHeight: 1.6 }}>
        {message}
      </p>
    </Modal>
  );
}
