import { REPO_URL } from "@/lib/constants";

export default function Footer() {
  return (
    <footer className="border-t border-shelf-200 bg-shelf-100/60">
      <div className="mx-auto flex max-w-6xl flex-col gap-2 px-4 py-6 text-sm text-shelf-600 sm:flex-row sm:items-center sm:justify-between">
        <p>© 2026 Shelfie · КГТУ им. И. Раззакова, ПИ-1-24</p>
        <div className="flex flex-wrap gap-4">
          <a className="hover:text-shelf-900" href={`${REPO_URL}/blob/main/docs/tz/tz.md`} target="_blank" rel="noreferrer">
            ТЗ
          </a>
          <a className="hover:text-shelf-900" href={`${REPO_URL}/blob/main/tasks/board.md`} target="_blank" rel="noreferrer">
            Задачи
          </a>
          <a className="hover:text-shelf-900" href={REPO_URL} target="_blank" rel="noreferrer">
            GitHub
          </a>
        </div>
      </div>
    </footer>
  );
}
