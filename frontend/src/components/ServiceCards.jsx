import React from 'react';
import { ChefHat, Car, Shield } from 'lucide-react';

const SERVICES = [
  {
    key: 'Cook',
    badge: 'Cook',
    icon: ChefHat,
    title: 'Home Cooking',
    price: '₹12,000 – ₹22,000 / mo',
    desc: 'Daily meal preparation for breakfast, lunch, or dinner. North Indian, South Indian, Continental, and specialized dietary cooking.',
    highlights: 'Tailored menus · Fresh ingredients · Hygiene compliant',
  },
  {
    key: 'Driver',
    badge: 'Driver',
    icon: Car,
    title: 'Personal Driver',
    price: '₹16,000 – ₹26,000 / mo',
    desc: 'Professional, verified drivers for daily city commuting, family school runs, or outstation trips. Manual and automatic vehicle expertise.',
    highlights: 'Commercial license · Clean driving record · Punctual',
  },
  {
    key: 'Security Guard',
    badge: 'Security Guard',
    icon: Shield,
    title: 'Premises Security',
    price: '₹14,000 – ₹22,000 / mo',
    desc: 'Trained security personnel for residential societies, individual villas, and commercial premises. Available for 12-hour or 24-hour shifts.',
    highlights: 'Visitor logging · Gate security · Emergency response',
  },
];

export default function ServiceCards({ onSelectService }) {
  return (
    <section className="mb-14">
      <div className="mb-6">
        <div className="uppercase tracking-[0.14em] text-[11px] font-bold text-[#C77F1F] mb-1">
          CHOOSE A SERVICE
        </div>
        <h2 className="font-serif text-2xl sm:text-3xl font-semibold text-[#16243F]">
          What help do you need today?
        </h2>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {SERVICES.map((s) => {
          const Icon = s.icon;
          return (
            <div
              key={s.key}
              className="service-card p-6 flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="w-10 h-10 rounded-xl bg-[#E8A33D]/12 flex items-center justify-center text-[#C77F1F]">
                    <Icon size={22} />
                  </div>
                  <span className="text-xs font-semibold px-2.5 py-0.5 rounded-full bg-[#F5F6F3] text-[#5B6573] border border-[#D9DDE2]">
                    {s.badge}
                  </span>
                </div>

                <h3 className="font-serif text-xl font-bold text-[#16243F] mb-1">
                  {s.title}
                </h3>
                <div className="text-sm font-semibold text-[#C77F1F] mb-3">
                  {s.price}
                </div>
                <p className="text-xs text-[#5B6573] leading-relaxed mb-4">
                  {s.desc}
                </p>
              </div>

              <div>
                <div className="text-[11px] text-[#5B6573] font-medium border-t border-[#D9DDE2] pt-3 mb-4">
                  {s.highlights}
                </div>
                <button
                  onClick={() => onSelectService(s.key)}
                  className="w-full bg-[#16243F] hover:bg-[#2B3A55] text-white text-xs font-semibold py-2.5 px-4 rounded-lg transition-colors cursor-pointer text-center shadow-sm"
                >
                  Select &amp; Specify Requirements
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
