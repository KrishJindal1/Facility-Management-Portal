import React from 'react';
import { User, LogOut, Building, ShieldCheck } from 'lucide-react';

export default function Header({
  tenants,
  currentTenant,
  onSelectTenant,
  currentUser,
  onOpenAuth,
  onLogout,
}) {
  const isAuthenticated = !!currentUser;

  return (
    <header className="border-b border-[#D9DDE2] pb-5 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        {/* Brand Logo & Tenant Tagline */}
        <div>
          <div className="font-serif text-2xl font-bold tracking-tight text-[#16243F]">
            Home<span className="text-[#C77F1F]">Desk</span>
          </div>
          <div className="text-xs text-[#5B6573] mt-0.5 flex items-center gap-1.5">
            <span>Facility Portal</span>
            <span>&middot;</span>
            <span className="font-semibold text-[#16243F]">
              {currentTenant ? currentTenant.name : 'HomeDesk Primary'}
            </span>
          </div>
        </div>

        {/* Right Action Bar */}
        <div className="flex items-center gap-3">
          {isAuthenticated ? (
            /* Authenticated User Pill & Logout */
            <div className="flex items-center gap-3 bg-white border border-[#D9DDE2] rounded-full pl-3 pr-2 py-1.5 shadow-sm">
              <div className="flex items-center gap-2">
                <div className="w-7 h-7 rounded-full bg-[#1F7A5C]/10 flex items-center justify-center text-[#1F7A5C]">
                  <User size={15} />
                </div>
                <div className="text-left pr-2">
                  <div className="text-xs font-semibold text-[#16243F] flex items-center gap-1">
                    {currentUser.name}
                    <span className="text-[10px] bg-[#1F7A5C]/12 text-[#1F7A5C] px-1.5 py-0.5 rounded-full font-bold">
                      {(currentUser.role || 'staff').toUpperCase()}
                    </span>
                  </div>
                  <div className="text-[10px] text-[#5B6573] flex items-center gap-1">
                    <Building size={10} />
                    <span>{currentUser.organization_name}</span>
                    <span className="text-[#C77F1F] font-medium">(Locked)</span>
                  </div>
                </div>
              </div>
              <button
                onClick={onLogout}
                className="text-xs flex items-center gap-1 text-[#5B6573] hover:text-[#16243F] hover:bg-[#F5F6F3] px-2 py-1 rounded-full transition-colors"
                title="Sign out"
              >
                <LogOut size={13} />
                <span className="hidden sm:inline">Sign out</span>
              </button>
            </div>
          ) : (
            /* Unauthenticated: Tenant Switcher & Sign In Button */
            <div className="flex items-center gap-2.5">
              {tenants && tenants.length > 1 && (
                <div className="relative">
                  <select
                    value={currentTenant?.id || ''}
                    onChange={(e) => onSelectTenant(Number(e.target.value))}
                    className="text-xs bg-white border border-[#D9DDE2] text-[#16243F] rounded-lg px-2.5 py-1.5 pr-7 appearance-none cursor-pointer focus:outline-none focus:border-[#E8A33D] shadow-sm font-medium"
                  >
                    {tenants.map((t) => (
                      <option key={t.id} value={t.id}>
                        🏢 {t.name}
                      </option>
                    ))}
                  </select>
                  <div className="pointer-events-none absolute right-2 top-1/2 -translate-y-1/2 text-[#5B6573] text-[10px]">
                    ▼
                  </div>
                </div>
              )}

              <button
                onClick={onOpenAuth}
                className="text-xs font-medium text-[#16243F] bg-white border border-[#D9DDE2] hover:border-[#16243F] px-3 py-1.5 rounded-lg shadow-sm transition-all flex items-center gap-1.5"
              >
                <User size={13} />
                <span>Staff Sign In</span>
              </button>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
