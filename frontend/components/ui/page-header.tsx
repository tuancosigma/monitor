import { type ReactNode } from "react";
import Link from "next/link";

interface Crumb {
  label: string;
  href?: string;
}

// Consistent page header: optional breadcrumb, title (h1), description, and a
// right-aligned actions slot. Title renders as an <h1> so existing accessible
// "heading" queries (and Playwright specs) keep matching by name.
export function PageHeader({
  title,
  description,
  breadcrumb,
  actions,
}: {
  title: string;
  description?: string;
  breadcrumb?: Crumb[];
  actions?: ReactNode;
}) {
  return (
    <header className="flex flex-wrap items-end justify-between gap-3">
      <div className="flex flex-col gap-1">
        {breadcrumb && breadcrumb.length > 0 && (
          <nav className="flex items-center gap-2 text-sm text-slate-400">
            {breadcrumb.map((c, i) => (
              <span key={c.label} className="flex items-center gap-2">
                {c.href ? (
                  <Link href={c.href} className="hover:text-slate-200">
                    {c.label}
                  </Link>
                ) : (
                  <span className="text-slate-200">{c.label}</span>
                )}
                {i < breadcrumb.length - 1 && <span>/</span>}
              </span>
            ))}
          </nav>
        )}
        <h1 className="h-display text-2xl font-semibold text-white">{title}</h1>
        {description && <p className="text-sm text-slate-400">{description}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </header>
  );
}
