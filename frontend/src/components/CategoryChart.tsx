import { useState } from 'react';
import type { CategoryTotal } from '../api/types';
import { useI18n } from '../i18n';
import { formatMoney } from '../utils/format';

const UNCATEGORIZED_COLOR = '#6b6b6b';
const SIZE = 180;
const CENTER = SIZE / 2;
const OUTER = 86;
const INNER = 58;
const GAP_COLOR = '#0d0d0d'; // card surface: draws the 2px gap between slices

interface Props {
  totals: CategoryTotal[];
  total: number;
  currency: string;
}

function point(radius: number, angle: number): string {
  return `${CENTER + radius * Math.sin(angle)} ${CENTER - radius * Math.cos(angle)}`;
}

function slicePath(start: number, end: number): string {
  const large = end - start > Math.PI ? 1 : 0;
  return [
    `M ${point(OUTER, start)}`,
    `A ${OUTER} ${OUTER} 0 ${large} 1 ${point(OUTER, end)}`,
    `L ${point(INNER, end)}`,
    `A ${INNER} ${INNER} 0 ${large} 0 ${point(INNER, start)}`,
    'Z',
  ].join(' ');
}

/** Donut of the month's costs per category. The legend doubles as the data table. */
export function CategoryChart({ totals, total, currency }: Props) {
  const [active, setActive] = useState<number | null>(null);
  const [tip, setTip] = useState<{ x: number; y: number } | null>(null);
  const { t } = useI18n();

  if (totals.length === 0 || total <= 0) {
    return <p className="muted">{t('chart.empty')}</p>;
  }

  const color = (item: CategoryTotal) => item.color || UNCATEGORIZED_COLOR;
  // Costs without a category come as one group; its name is translated here
  const name = (item: CategoryTotal) => (item.category_id ? item.name : t('category.uncategorized'));
  const pct = (value: number) => `${Math.round((value / total) * 100)}%`;
  let angle = 0;
  const slices = totals.map((item) => {
    const start = angle;
    angle += (item.total / total) * Math.PI * 2;
    return { start, end: angle };
  });
  const activeItem = active !== null ? totals[active] : null;

  return (
    <div className="category-chart">
      <svg
        className="category-chart__svg"
        viewBox={`0 0 ${SIZE} ${SIZE}`}
        role="img"
        aria-label={t('chart.ariaLabel', {
          list: totals.map((item) => `${name(item)} ${formatMoney(item.total, currency)}`).join(', '),
        })}
        onMouseLeave={() => {
          setActive(null);
          setTip(null);
        }}
      >
        {totals.length === 1 ? (
          <circle
            cx={CENTER}
            cy={CENTER}
            r={(OUTER + INNER) / 2}
            fill="none"
            stroke={color(totals[0])}
            strokeWidth={OUTER - INNER}
            onMouseMove={(e) => {
              setActive(0);
              setTip({ x: e.clientX, y: e.clientY });
            }}
          />
        ) : (
          slices.map((s, i) => (
            <path
              key={totals[i].category_id ?? 'none'}
              d={slicePath(s.start, s.end)}
              fill={color(totals[i])}
              stroke={GAP_COLOR}
              strokeWidth={2}
              opacity={active === null || active === i ? 1 : 0.45}
              onMouseMove={(e) => {
                setActive(i);
                setTip({ x: e.clientX, y: e.clientY });
              }}
              onClick={() => setActive(active === i ? null : i)}
            />
          ))
        )}
        <text x={CENTER} y={CENTER - 4} textAnchor="middle" fill="#8c8c8c" fontSize="11">
          {activeItem ? name(activeItem) : t('chart.total')}
        </text>
        <text x={CENTER} y={CENTER + 14} textAnchor="middle" fill="#f5f5f5" fontSize="15" fontWeight="700">
          {formatMoney(activeItem ? activeItem.total : total, currency)}
        </text>
      </svg>

      <ul className="category-chart__legend">
        {totals.map((item, i) => (
          <li
            key={item.category_id ?? 'none'}
            className={`legend-item ${active === i ? 'legend-item--active' : ''}`}
            onMouseEnter={() => setActive(i)}
            onMouseLeave={() => setActive(null)}
          >
            <span className="legend-item__swatch" style={{ background: color(item) }} />
            <span>{name(item)}</span>
            <span className="num">{formatMoney(item.total, currency)}</span>
            <span className="legend-item__pct">{pct(item.total)}</span>
          </li>
        ))}
      </ul>

      {tip && activeItem && (
        <div className="chart-tooltip" style={{ left: tip.x + 12, top: tip.y + 12 }}>
          <strong>{name(activeItem)}</strong> · {formatMoney(activeItem.total, currency)} ({pct(activeItem.total)})
        </div>
      )}
    </div>
  );
}
