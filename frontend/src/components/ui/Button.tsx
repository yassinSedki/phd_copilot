import { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "md" | "sm";
  loading?: boolean;
  icon?: ReactNode;
  square?: boolean;
}

const VARIANT_CLASS: Record<Variant, string> = {
  primary: "btn-primary",
  secondary: "btn-secondary",
  ghost: "btn-ghost",
  danger: "btn-danger",
};

export default function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  icon,
  square = false,
  disabled,
  className = "",
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    "btn",
    "tr",
    VARIANT_CLASS[variant],
    size === "sm" ? "btn-sm" : "",
    square ? "btn-square" : "",
    className,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} disabled={disabled || loading} {...rest}>
      {loading ? (
        <span className={`spinner ${variant !== "primary" ? "spinner-dark" : ""}`} />
      ) : (
        <>
          {icon}
          {children}
        </>
      )}
    </button>
  );
}
