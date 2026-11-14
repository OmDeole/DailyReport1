import React, { useState, useRef } from 'react';
import { FullDashboardPayload } from '../../types';
import * as XLSX from 'xlsx';
import { X, Upload, RotateCcw, Download, CheckCircle2, AlertCircle, Loader2, CloudUpload } from 'lucide-react';
import { uploadReportPackage, getCommentsExcelExportUrl } from '../../utils/api';

interface DataImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onImportData: (payload: FullDashboardPayload) => void;
  onResetToDemo: () => void;
  currentData: FullDashboardPayload;
}

export const DataImportModal: React.FC<DataImportModalProps> = ({
  isOpen,
  onClose,
  onImportData,
  onResetToDemo,
  currentData
}) => {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const backendInputRef = useRef<HTMLInputElement>(null);
  const [importStatus, setImportStatus] = useState<{ msg: string; isError?: boolean } | null>(null);
  const [isUploading, setIsUploading] = useState<boolean>(false);

  if (!isOpen) return null;

  // Handles upload directly to Django + PostgreSQL backend
  const handleBackendUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files || files.length === 0) return;

    setIsUploading(true);
    setImportStatus({ msg: 'Uploading and parsing Excel package on server...' });

    try {
      const formData = new FormData();
      if (files.length === 1 && files[0].name.toLowerCase().endsWith('.zip')) {
        formData.append('archive', files[0]);
      } else {
        for (let i = 0; i < files.length; i++) {
          formData.append(`file_${i}`, files[i]);
        }
      }

      const res = await uploadReportPackage(formData);
      if (res.success && res.payload) {
        onImportData(res.payload);
        setImportStatus({
          msg: `✅ Server published report successfully for cutoff ${res.cutoff_date}! All intranet users can now see this report.`,
          isError: false,
        });
      } else {
        setImportStatus({
          msg: `Upload error: ${res.error || 'Server could not process files'}`,
          isError: true,
        });
      }
    } catch (err: any) {
      setImportStatus({
        msg: `Failed to upload to server: ${err.message}`,
        isError: true,
      });
    } finally {
      setIsUploading(false);
      if (backendInputRef.current) backendInputRef.current.value = '';
    }
  };

  // Local fallback parser
  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    const fileName = file.name.toLowerCase();

    if (fileName.endsWith('.json')) {
      reader.onload = evt => {
        try {
          const parsed = JSON.parse(evt.target?.result as string);
          if (parsed && parsed.meta && parsed.demand) {
            onImportData(parsed);
            setImportStatus({ msg: `Successfully imported JSON dataset (${file.name})` });
          } else {
            setImportStatus({ msg: 'Invalid JSON schema: Missing meta or demand fields', isError: true });
          }
        } catch (err: any) {
          setImportStatus({ msg: 'Failed to parse JSON file: ' + err.message, isError: true });
        }
      };
      reader.readAsText(file);
    } else if (fileName.endsWith('.xlsx') || fileName.endsWith('.xls')) {
      reader.onload = evt => {
        try {
          const data = new Uint8Array(evt.target?.result as ArrayBuffer);
          const workbook = XLSX.read(data, { type: 'array' });
          
          const sheetNames = workbook.SheetNames;
          if (sheetNames.includes('Comments')) {
            const commentsSheet = workbook.Sheets['Comments'];
            const jsonComments = XLSX.utils.sheet_to_json<any>(commentsSheet);
            
            const importedComments = jsonComments.map((r, idx) => ({
              id: r['ID'] || r['id'] || `C${String(idx + 1).padStart(4, '0')}`,
              created: r['Created'] || r['created'] || new Date().toISOString().slice(0, 19).replace('T', ' '),
              updated: r['Last Updated'] || r['updated'] || new Date().toISOString().slice(0, 19).replace('T', ' '),
              part: String(r['Part Number'] || r['part'] || '').trim(),
              desc: String(r['Description'] || r['desc'] || '').trim(),
              customer: String(r['Customer'] || r['customer'] || '').trim(),
              minifactory: String(r['Minifactory'] || r['minifactory'] || '').trim(),
              line: String(r['Line'] || r['line'] || '').trim(),
              stakeholder: String(r['Stakeholder'] || r['stakeholder'] || '').trim(),
              category: String(r['Issue Category'] || r['category'] || 'Other').trim(),
              discussion: String(r['Stakeholder Input / Discussion'] || r['discussion'] || '').trim(),
              action: String(r['Action Being Taken'] || r['action'] || '').trim(),
              owner: String(r['Owner'] || r['owner'] || '').trim(),
              target_date: String(r['Target Date'] || r['target_date'] || '').trim(),
              status: String(r['Status'] || r['status'] || 'Open').trim(),
              criticality: String(r['Control Status'] || r['criticality'] || 'Critical').trim(),
              needs_escalation: String(r['Needs Escalation'] || r['needs_escalation'] || 'No').trim(),
              escalation_details: String(r['Escalation Details'] || r['escalation_details'] || '').trim(),
              plan_val: Number(r['Plan Value (INR) at entry'] || r['plan_val'] || 0),
              pending_val: Number(r['Pending Value (INR) at entry'] || r['pending_val'] || 0)
            }));

            const updatedData = { ...currentData, comments: importedComments };
            onImportData(updatedData);
            setImportStatus({ msg: `Successfully imported ${importedComments.length} comments from ${file.name}` });
          } else {
            setImportStatus({
              msg: `Excel workbook loaded (${sheetNames.join(', ')}). To upload raw data package to server, use the 'Publish to Plant Server' button above.`,
              isError: false
            });
          }
        } catch (err: any) {
          setImportStatus({ msg: 'Failed to process Excel workbook: ' + err.message, isError: true });
        }
      };
      reader.readAsArrayBuffer(file);
    }
  };

  const handleExportBackup = () => {
    const jsonStr = JSON.stringify(currentData, null, 2);
    const blob = new Blob([jsonStr], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `KSPG_Command_Center_Backup_${currentData.meta.cutoff_date}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 flex items-center justify-center p-4 backdrop-blur-xs select-none">
      <div className="bg-[var(--bg-panel)] border border-[var(--border)] rounded-lg shadow-2xl max-w-xl w-full p-4 flex flex-col gap-3">
        {/* Modal Header */}
        <div className="flex items-center justify-between border-b border-[var(--border)] pb-2.5">
          <div className="flex items-center gap-2">
            <CloudUpload className="w-5 h-5 text-blue-400" />
            <span className="font-extrabold text-[14px] text-[var(--text-main)]">
              Daily Report Data Management
            </span>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded text-slate-400 hover:text-white hover:bg-[var(--bg-card)] cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Status message */}
        {importStatus && (
          <div
            className={`flex items-center gap-2 px-3 py-2 rounded text-xs font-semibold ${
              importStatus.isError
                ? 'bg-rose-500/15 border border-rose-500/40 text-rose-400'
                : 'bg-emerald-500/15 border border-emerald-500/40 text-emerald-400'
            }`}
          >
            {isUploading ? (
              <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin text-blue-400" />
            ) : importStatus.isError ? (
              <AlertCircle className="w-4 h-4 flex-shrink-0" />
            ) : (
              <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
            )}
            <span>{importStatus.msg}</span>
          </div>
        )}

        {/* Primary Action: Upload to Intranet Central Server */}
        <div
          onClick={() => !isUploading && backendInputRef.current?.click()}
          className="border-2 border-dashed border-blue-500/70 hover:border-blue-400 bg-blue-500/10 hover:bg-blue-500/15 rounded-lg p-5 flex flex-col items-center justify-center text-center gap-2 cursor-pointer transition-all"
        >
          {isUploading ? (
            <Loader2 className="w-9 h-9 text-blue-400 animate-spin" />
          ) : (
            <CloudUpload className="w-9 h-9 text-blue-400" />
          )}
          <div className="text-[13px] font-extrabold text-white">
            Publish New Daily Package to Server (All Intranet Users)
          </div>
          <div className="text-[11px] text-slate-300 max-w-md">
            Upload the 8 Excel files (<span className="text-blue-300">Calendar, Demand, MB51, MB52, Price, Vendor, Exchange, Master</span>) or a single <strong className="text-white">.ZIP</strong> archive. The server will calculate and immediately broadcast to the plant.
          </div>
          <input
            ref={backendInputRef}
            type="file"
            multiple
            accept=".xlsx,.xls,.zip"
            onChange={handleBackendUpload}
            className="hidden"
            disabled={isUploading}
          />
        </div>

        {/* Overview of current loaded data */}
        <div className="bg-[var(--bg-card)] border border-[var(--border)] rounded p-3 text-xs space-y-1.5">
          <div className="font-bold text-slate-200 uppercase text-[10.5px] tracking-wide">
            Active Dataset Overview
          </div>
          <div className="grid grid-cols-2 gap-2 text-[11px] text-slate-300">
            <div>
              ● Demand FG Parts: <strong className="text-white">{currentData.demand.length}</strong>
            </div>
            <div>
              ● Monitored RMPM Parts: <strong className="text-white">{currentData.rmpm_parts.length}</strong>
            </div>
            <div>
              ● MB51 Ledger Rows: <strong className="text-white">{currentData.mb51.length}</strong>
            </div>
            <div>
              ● MB52 Stock Items: <strong className="text-white">{currentData.mb52.length}</strong>
            </div>
            <div>
              ● Working Days: <strong className="text-white">{currentData.meta.total_working_days}</strong> ({currentData.meta.elapsed_working_days} elapsed)
            </div>
            <div>
              ● Comments Logged: <strong className="text-emerald-400">{currentData.comments.length}</strong>
            </div>
          </div>
        </div>

        {/* Action Buttons */}
        <div className="flex items-center justify-between border-t border-[var(--border)] pt-3 gap-2 flex-wrap">
          <button
            onClick={() => {
              if (confirm('Reset entire application to built-in Kolbenschmidt Pierburg (KSPG) sample dataset?')) {
                onResetToDemo();
                setImportStatus({ msg: 'Restored original comprehensive demo dataset.' });
              }
            }}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-amber-500/40 text-amber-400 bg-[var(--bg-card)] hover:bg-amber-500/15 text-xs font-bold cursor-pointer"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>Reset Demo Data</span>
          </button>

          <div className="flex items-center gap-2 ml-auto">
            <a
              href={getCommentsExcelExportUrl()}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-emerald-500/40 text-emerald-400 bg-[var(--bg-card)] hover:bg-emerald-500/15 text-xs font-bold cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download Comments Excel</span>
            </a>

            <button
              onClick={handleExportBackup}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Download JSON Backup</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
