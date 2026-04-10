export type PageKey = 'overview' | 'explorer' | 'vintages' | 'methodology'

type NavTabsProps = {
  page: PageKey
  labels: Record<PageKey, string>
  onSelect: (page: PageKey) => void
}

export function NavTabs({ page, labels, onSelect }: NavTabsProps) {
  const pages = Object.keys(labels) as PageKey[]

  return (
    <nav className="nav-tabs" aria-label="Dashboard sections">
      {pages.map((item) => (
        <button
          key={item}
          type="button"
          className={item === page ? 'nav-tab is-active' : 'nav-tab'}
          onClick={() => onSelect(item)}
        >
          {labels[item]}
        </button>
      ))}
    </nav>
  )
}
