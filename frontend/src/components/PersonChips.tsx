import type { Member } from '../api/types';

interface PersonChipsProps {
  /** Members already ordered by the API: residents A-Z, then guests A-Z */
  members: Member[];
  selected: string[];
  onChange: (ids: string[]) => void;
  label: string;
  /** Show "Everyone" / "Residents" shortcuts */
  shortcuts?: boolean;
}

const isResident = (m: Member) => m.role === 'manager' || m.role === 'resident';

export function PersonChips({ members, selected, onChange, label, shortcuts }: PersonChipsProps) {
  const residents = members.filter(isResident);
  const guests = members.filter((m) => m.role === 'guest');
  const toggle = (id: string) =>
    onChange(selected.includes(id) ? selected.filter((s) => s !== id) : [...selected, id]);
  const sameSet = (ids: string[]) => ids.length === selected.length && ids.every((id) => selected.includes(id));

  const chip = (m: Member) => {
    const isOn = selected.includes(m.id);
    return (
      <button
        type="button"
        key={m.id}
        className={`chip ${isOn ? 'chip--selected' : ''}`}
        onClick={() => toggle(m.id)}
        aria-pressed={isOn}
      >
        {isOn && <span className="chip__check">✓</span>}
        {m.display_name}
        {!m.is_active && <span className="muted small">(disabled)</span>}
      </button>
    );
  };

  return (
    <div role="group" aria-label={label}>
      <div className="chips">
        {residents.map(chip)}
        {guests.length > 0 && <div className="chips-divider">Guests</div>}
        {guests.map(chip)}
      </div>
      {shortcuts && (
        <div className="chips" style={{ marginTop: 10 }}>
          <button
            type="button"
            className={`chip chip--small ${sameSet(members.map((m) => m.id)) ? 'chip--selected' : ''}`}
            onClick={() => onChange(members.map((m) => m.id))}
          >
            Everyone
          </button>
          {guests.length > 0 && (
            <button
              type="button"
              className={`chip chip--small ${sameSet(residents.map((m) => m.id)) ? 'chip--selected' : ''}`}
              onClick={() => onChange(residents.map((m) => m.id))}
            >
              Residents only
            </button>
          )}
          <button type="button" className="chip chip--small" onClick={() => onChange([])}>
            Clear
          </button>
        </div>
      )}
    </div>
  );
}
