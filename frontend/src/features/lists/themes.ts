import type { ListTheme } from "@/lib/types";

/**
 * Темы витрины различаются не только цветом: у каждой свой фон, шрифт заголовка,
 * форма карточек и вид заметки. Классы записаны целиком, чтобы Tailwind их увидел.
 */
export interface ThemeStyle {
  page: string;
  title: string;
  lead: string;
  card: string;
  index: string;
  cardTitle: string;
  meta: string;
  note: string;
  chip: string;
  swatch: string;
}

export const LIST_THEMES: Record<ListTheme, ThemeStyle> = {
  classic: {
    page: "bg-shelf-50 text-shelf-900",
    title: "font-serif text-4xl font-semibold tracking-tight text-shelf-900",
    lead: "text-shelf-700",
    card: "rounded-2xl bg-white ring-1 ring-shelf-200 shadow-sm",
    index: "bg-shelf-900 text-shelf-50 rounded-full",
    cardTitle: "text-shelf-900 font-semibold",
    meta: "text-shelf-500",
    note: "border-l-4 border-accent-600 bg-shelf-100 text-shelf-800 rounded-r-lg",
    chip: "bg-shelf-200 text-shelf-800",
    swatch: "bg-gradient-to-br from-shelf-50 to-shelf-300",
  },
  noir: {
    page: "bg-neutral-950 text-neutral-100",
    title: "font-mono text-4xl font-bold uppercase tracking-[0.2em] text-white",
    lead: "text-neutral-400",
    card: "rounded-none bg-neutral-900 ring-1 ring-neutral-700",
    index: "bg-white text-black rounded-none font-mono",
    cardTitle: "text-white font-bold uppercase tracking-wide",
    meta: "text-neutral-500",
    note: "border border-dashed border-neutral-600 bg-black/40 text-neutral-300 font-mono",
    chip: "bg-neutral-800 text-neutral-200",
    swatch: "bg-gradient-to-br from-neutral-950 to-neutral-600",
  },
  pastel: {
    page: "bg-gradient-to-b from-rose-50 via-violet-50 to-sky-50 text-slate-800",
    title: "font-sans text-4xl font-extrabold tracking-tight text-violet-700",
    lead: "text-slate-600",
    card: "rounded-3xl bg-white/80 ring-2 ring-rose-100 shadow-lg shadow-violet-100",
    index: "bg-rose-300 text-white rounded-2xl",
    cardTitle: "text-violet-800 font-bold",
    meta: "text-slate-500",
    note: "rounded-2xl bg-amber-50 text-amber-900 ring-1 ring-amber-200 italic",
    chip: "bg-violet-100 text-violet-700",
    swatch: "bg-gradient-to-br from-rose-200 via-violet-200 to-sky-200",
  },
};
