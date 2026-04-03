type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'info';

interface BadgeProps {
  children: React.ReactNode;
  variant?: BadgeVariant;
  className?: string;
}

const variantStyles: Record<BadgeVariant, string> = {
  default: 'bg-gray-800 text-gray-300',
  success: 'bg-green-900/30 text-green-400 border border-green-800',
  warning: 'bg-yellow-900/30 text-yellow-400 border border-yellow-800',
  error: 'bg-red-900/30 text-red-400 border border-red-800',
  info: 'bg-blue-900/30 text-blue-400 border border-blue-800',
};

export default function Badge({ children, variant = 'default', className = '' }: BadgeProps) {
  return (
    <span
      className={`inline-flex items-center px-2 py-1 rounded text-xs font-medium ${variantStyles[variant]} ${className}`}
    >
      {children}
    </span>
  );
}
