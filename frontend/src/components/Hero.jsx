import React from 'react';
import TokenCard from './TokenCard';
import { CheckCircle } from 'lucide-react';

export default function Hero({
  currentTenant,
  activeRequest,
  onSaveRequest,
  onClearRequest,
}) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center mb-12">
      {/* Left Column: Heading and Value Proposition */}
      <div className="lg:col-span-7">
        <div className="uppercase tracking-[0.14em] text-xs font-bold text-[#C77F1F] mb-3">
          VERIFIED DOMESTIC & FACILITY STAFF
        </div>
        <h1 className="font-serif text-3xl sm:text-4xl md:text-5xl font-semibold leading-[1.15] text-[#16243F] mb-4">
          Trusted help for your home, without the hassle.
        </h1>
        <p className="text-[#5B6573] text-sm sm:text-base leading-relaxed max-w-xl mb-6">
          Pre-vetted cooks, verified personal drivers, and trained security personnel —
          matched to your schedule and household standards.
        </p>

        {/* Trust Badges */}
        <div className="flex flex-wrap items-center gap-x-5 gap-y-2 text-xs font-medium text-[#16243F]">
          <div className="flex items-center gap-1.5">
            <CheckCircle size={14} className="text-[#1F7A5C]" />
            <span>Identity & address verification</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle size={14} className="text-[#1F7A5C]" />
            <span>Transparent pricing tiers</span>
          </div>
          <div className="flex items-center gap-1.5">
            <CheckCircle size={14} className="text-[#1F7A5C]" />
            <span>Prompt tenant replacement</span>
          </div>
        </div>
      </div>

      {/* Right Column: Signature Token Card */}
      <div className="lg:col-span-5 flex justify-end">
        <TokenCard
          currentTenant={currentTenant}
          activeRequest={activeRequest}
          onSaveRequest={onSaveRequest}
          onClearRequest={onClearRequest}
        />
      </div>
    </div>
  );
}
