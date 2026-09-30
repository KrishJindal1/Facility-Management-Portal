import React, { useState } from 'react';
import { FileSpreadsheet, Download, ChevronDown, ChevronUp } from 'lucide-react';
import { downloadExcelExport } from '../api';

export default function Footer({ currentTenant }) {
  const [isExportOpen, setIsExportOpen] = useState(false);
  const [isDownloading, setIsDownloading] = useState(false);
  const [exportError, setExportError] = useState('');

  const handleDownload = async () => {
    setIsDownloading(true);
    setExportError('');
    try {
      const orgId = currentTenant ? currentTenant.id : 1;
      const slug = currentTenant?.slug || 'leads';
      await downloadExcelExport(orgId, `${slug}_leads.xlsx`);
    } catch (err) {
      setExportError(err.message || 'Export unavailable');
    } finally {
      setIsDownloading(false);
    }
  };

  const tenantName = currentTenant ? currentTenant.name : 'HomeDesk';

  return (
    <footer className="border-t border-[#D9DDE2] pt-8 pb-12 mt-12 text-[#5B6573]">
      {/* Excel Export Accordion */}
      <div className="bg-white border border-[#D9DDE2] rounded-xl overflow-hidden mb-8 max-w-xl mx-auto shadow-sm">
        <button
          onClick={() => setIsExportOpen(!isExportOpen)}
          className="w-full flex items-center justify-between p-4 text-xs font-semibold text-[#16243F] hover:bg-[#F5F6F3] transition-colors"
        >
          <div className="flex items-center gap-2">
            <FileSpreadsheet size={16} className="text-[#1F7A5C]" />
            <span>Export {tenantName} Leads to Excel (Admin / Reports)</span>
          </div>
          {isExportOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>

        {isExportOpen && (
          <div className="p-4 border-t border-[#D9DDE2] bg-[#F5F6F3]/50">
            <p className="text-xs text-[#5B6573] mb-3">
              Download all requirements, customer contacts, and assigned lead IDs scoped strictly to <b>{tenantName}</b>.
            </p>

            {exportError && (
              <div className="text-xs text-red-600 mb-2">{exportError}</div>
            )}

            <button
              onClick={handleDownload}
              disabled={isDownloading}
              className="w-full bg-[#1F7A5C] hover:bg-[#165a44] text-white text-xs font-semibold py-2.5 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
            >
              <Download size={14} />
              <span>{isDownloading ? 'Generating Spreadsheet...' : `Download ${tenantName} Leads (.xlsx)`}</span>
            </button>
          </div>
        )}
      </div>

      {/* Footer Notes */}
      <div className="text-center text-xs space-y-2">
        <p className="font-medium text-[#16243F]">
          No spam calls. Just genuine requests, routed straight to your inbox.
        </p>
        <p className="text-[11px] text-[#5B6573]/80">
          &copy; {new Date().getFullYear()} HomeDesk Cloud Facility Management Platform &middot; Multi-Tenant Architecture.
        </p>
      </div>
    </footer>
  );
}
