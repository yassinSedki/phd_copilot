interface Option<T extends string> {
  value: T;
  label: string;
}

interface SegmentedControlProps<T extends string> {
  options: Option<T>[];
  value: T | null;
  onChange: (value: T) => void;
}

export default function SegmentedControl<T extends string>({ options, value, onChange }: SegmentedControlProps<T>) {
  return (
    <div className="segmented">
      {options.map((opt) => (
        <div
          key={opt.value}
          className={`segmented-option tr ${value === opt.value ? "active" : ""}`}
          onClick={() => onChange(opt.value)}
          role="button"
          tabIndex={0}
        >
          {opt.label}
        </div>
      ))}
    </div>
  );
}
