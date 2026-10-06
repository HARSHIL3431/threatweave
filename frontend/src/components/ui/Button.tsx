import { cn } from "@/lib/utils";

export function Button({
  children, variant = "primary", className = "", ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { variant?: "primary" | "outline" }) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-[10px] px-5 py-2.5 text-sm font-semibold transition-all",
        variant === "primary" && "text-white shadow-lg",
        variant === "outline" && "border bg-transparent",
        className
      )}
      style={
        variant === "primary"
          ? { backgroundImage: "linear-gradient(to bottom, var(--brand-grad-from), var(--brand-grad-to))", boxShadow: "var(--active-glow)" }
          : { borderColor: "var(--border)", color: "var(--text)" }
      }
      {...props}
    >
      {children}
    </button>
  );
}
