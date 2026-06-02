import { MODEL_FAMILIES, type ModelFamily } from '../modelFamily'

type ModelSelectorProps = {
  value: ModelFamily
  onChange: (value: ModelFamily) => void
}

export default function ModelSelector({ value, onChange }: ModelSelectorProps) {
  return (
    <div className="model-switch" aria-label="Model family">
      {MODEL_FAMILIES.map((family) => (
        <button
          key={family.value}
          type="button"
          onClick={() => onChange(family.value)}
          className={value === family.value ? 'model-switch-option model-switch-option-active' : 'model-switch-option'}
          aria-pressed={value === family.value}
          title={family.label}
        >
          <span className="hidden sm:inline">{family.label}</span>
          <span className="sm:hidden">{family.shortLabel}</span>
        </button>
      ))}
    </div>
  )
}
