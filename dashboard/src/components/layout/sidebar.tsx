'use client';

import Image from 'next/image';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  LayoutDashboard,
  FileText,
  ClipboardList,
  Database,
  CheckCircle,
  Settings,
  HelpCircle,
  ExternalLink,
} from 'lucide-react';
import { useApprovals } from '@/lib/hooks';

const navigation = [
  { name: 'Dashboard', href: '/', icon: LayoutDashboard },
  { name: 'Policies', href: '/policies', icon: FileText },
  { name: 'Governance', href: '/governance', icon: ClipboardList },
  { name: 'Evidence', href: '/evidence', icon: Database },
  { name: 'Approvals', href: '/approvals', icon: CheckCircle, badge: true },
  { name: 'Settings', href: '/settings', icon: Settings },
];

const resources = [
  { name: 'Documentation', href: 'https://stix.dev/docs', external: true },
  { name: 'API Reference', href: 'https://stix.dev/api', external: true },
  { name: 'Support', href: 'https://stix.dev/support', external: true },
];

export function Sidebar() {
  const pathname = usePathname();
  const { data: pendingData } = useApprovals({ status: 'PENDING', page_size: 1 });
  const pendingCount = pendingData?.total || 0;

  return (
    <aside className="fixed inset-y-0 left-0 w-64 bg-slate-800 flex flex-col">
      {/* Logo */}
      <div className="flex items-center justify-center px-4 py-6 bg-white border-b border-slate-700">
        <Image
          src="/images/logo-wordmark.png"
          alt="STIX"
          width={220}
          height={56}
          className="object-contain"
          priority
        />
      </div>

      {/* Main Navigation */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <p className="px-3 text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
          Main
        </p>
        {navigation.map((item) => {
          const isActive = pathname === item.href;
          const Icon = item.icon;

          return (
            <Link
              key={item.name}
              href={item.href}
              className={`
                flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium
                transition-colors duration-150
                ${isActive
                  ? 'bg-slate-700 text-white'
                  : 'text-gray-400 hover:text-white hover:bg-slate-700'
                }
              `}
            >
              <Icon className="h-5 w-5" />
              <span className="flex-1">{item.name}</span>
              {item.badge && pendingCount > 0 && (
                <span className="px-2 py-0.5 text-xs font-medium bg-yellow-500 text-yellow-900 rounded-full">
                  {pendingCount}
                </span>
              )}
            </Link>
          );
        })}

        <div className="pt-6">
          <p className="px-3 text-xs font-medium text-gray-500 uppercase tracking-wider mb-2">
            Resources
          </p>
          {resources.map((item) => (
            <a
              key={item.name}
              href={item.href}
              target={item.external ? '_blank' : undefined}
              rel={item.external ? 'noopener noreferrer' : undefined}
              className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-slate-700"
            >
              <HelpCircle className="h-5 w-5" />
              <span className="flex-1">{item.name}</span>
              {item.external && <ExternalLink className="h-4 w-4" />}
            </a>
          ))}
        </div>
      </nav>

      {/* Footer */}
      <div className="px-6 py-4 border-t border-slate-700">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-full bg-gray-700 flex items-center justify-center">
            <span className="text-sm font-medium text-white">A</span>
          </div>
          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-white truncate">Admin</p>
            <p className="text-xs text-gray-400 truncate">admin@example.com</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
