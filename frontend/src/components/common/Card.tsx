interface CardProps {
  children: React.ReactNode;
  className?: string;
  title?: string;
}

export default function Card({ children, className = '', title }: CardProps) {
  return (
    <div className={`bg-gray-900/50 border border-gray-800 rounded-lg ${className}`}>
      {title && (
        <div className="px-6 py-4 border-b border-gray-800">
          <h3 className="text-lg font-semibold text-gray-100">{title}</h3>
        </div>
      )}
      <div className="p-6">{children}</div>
    </div>
  );
}
