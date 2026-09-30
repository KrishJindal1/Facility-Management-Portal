import React, { useState } from 'react';
import { Search, ChevronDown, ChevronUp, CheckCircle2, AlertCircle } from 'lucide-react';
import { lookupLead } from '../api';

export default function TokenCard({
  currentTenant,
  activeRequest,
  onSaveRequest,
  onClearRequest,
}) {
  const [mobileInput, setMobileInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [showDetails, setShowDetails] = useState(false);
  const [detailsData, setDetailsData] = useState(null);

  const handleLookup = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    const clean = mobileInput.trim();

    if (!clean) {
      setErrorMsg('Please enter your 10-digit mobile number first.');
      return;
    }

    if (!/^\d{10}$/.test(clean)) {
      setErrorMsg('Mobile number must be exactly 10 digits.');
      return;
    }

    setIsLoading(true);
    try {
      const orgId = currentTenant ? currentTenant.id : 1;
      const found = await lookupLead(clean, orgId);

      if (found) {
        onSaveRequest({
          lead_id: found['Lead ID'],
          mobile: clean,
          service: found['Service'] || found['Service Type'] || 'Cook',
          details: found,
        });
        setDetailsData(found);
        setMobileInput('');
      } else {
        setErrorMsg('No active request found for this mobile number in this organization.');
      }
    } catch (err) {
      setErrorMsg(err.message || 'Lookup failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const toggleDetails = async () => {
    if (!showDetails && !detailsData && activeRequest?.mobile) {
      setIsLoading(true);
      try {
        const orgId = currentTenant ? currentTenant.id : 1;
        const data = await lookupLead(activeRequest.mobile, orgId);
        setDetailsData(data);
      } catch (err) {
        // Fallback
      } finally {
        setIsLoading(false);
      }
    }
    setShowDetails(!showDetails);
  };

  return (
    <div className="token-card max-w-[340px] w-full ml-auto">
      {activeRequest ? (
        /* State 1: User has an active tracked lead token */
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[#5B6573] font-semibold mb-1">
            YOUR REQUEST ({currentTenant ? currentTenant.name : 'HomeDesk'})
          </div>
          <div className="font-mono text-2xl font-bold text-[#16243F] mb-3">
            {activeRequest.lead_id || '—'}
          </div>

          <div className="token-perforation my-3"></div>

          <div className="flex items-center justify-between py-2 text-xs">
            <span className="font-medium text-[#16243F] uppercase tracking-wide">
              {activeRequest.service || 'SERVICE'}
            </span>
            <span className="bg-[#1F7A5C]/12 text-[#1F7A5C] px-2.5 py-0.5 rounded-full font-semibold text-[11px] flex items-center gap-1">
              <CheckCircle2 size={11} />
              SUBMITTED
            </span>
          </div>

          {/* Expandable Details */}
          <div className="border-t border-[#D9DDE2] pt-2 mt-2">
            <button
              onClick={toggleDetails}
              className="w-full flex items-center justify-between text-xs text-[#5B6573] hover:text-[#16243F] font-medium py-1 transition-colors"
            >
              <span>View request details</span>
              {showDetails ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>

            {showDetails && (
              <div className="mt-2 p-2.5 bg-[#F5F6F3] rounded-lg text-xs space-y-1.5 max-h-48 overflow-y-auto">
                {detailsData ? (
                  Object.entries(detailsData).map(([k, v]) => (
                    <div key={k} className="flex justify-between border-b border-[#D9DDE2]/50 pb-1 last:border-none">
                      <span className="text-[#5B6573] font-medium">{k}:</span>
                      <span className="text-[#16243F] font-semibold text-right max-w-[170px] truncate">{String(v)}</span>
                    </div>
                  ))
                ) : (
                  <div className="text-[#5B6573] italic text-center py-1">Loading details...</div>
                )}
              </div>
            )}
          </div>

          <button
            onClick={onClearRequest}
            className="w-full mt-3 text-xs text-[#5B6573] hover:text-[#16243F] bg-white border border-[#D9DDE2] hover:bg-[#F5F6F3] py-1.5 rounded-lg transition-colors font-medium"
          >
            Not you? Clear this
          </button>
        </div>
      ) : (
        /* State 2: Find request form */
        <div>
          <div className="text-[11px] uppercase tracking-wider text-[#5B6573] font-semibold mb-1">
            FIND YOUR REQUEST ({currentTenant ? currentTenant.name : 'HomeDesk'})
          </div>
          <div className="text-base font-semibold text-[#16243F] mb-3">
            Track an existing request
          </div>

          <div className="token-perforation my-3"></div>

          <form onSubmit={handleLookup} className="space-y-2.5 mt-3">
            <div>
              <input
                type="tel"
                maxLength={10}
                placeholder="10-digit mobile number"
                value={mobileInput}
                onChange={(e) => setMobileInput(e.target.value.replace(/\D/g, ''))}
                className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white text-[#16243F] placeholder-[#5B6573]/70 focus:outline-none focus:border-[#E8A33D] font-mono shadow-inner"
              />
            </div>

            {errorMsg && (
              <div className="text-[11px] text-[#C77F1F] bg-[#E8A33D]/10 p-2 rounded-md flex items-start gap-1.5">
                <AlertCircle size={13} className="shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={isLoading}
              className="w-full bg-[#E8A33D] hover:bg-[#C77F1F] text-white text-xs font-semibold py-2 px-3 rounded-lg transition-colors shadow-sm flex items-center justify-center gap-1.5 disabled:opacity-50 cursor-pointer"
            >
              <Search size={13} />
              <span>{isLoading ? 'Searching...' : 'Find my request'}</span>
            </button>
          </form>
        </div>
      )}
    </div>
  );
}
