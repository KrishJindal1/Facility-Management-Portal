import React, { useState } from 'react';
import { X, Lock, Mail, User, Phone, Building, AlertCircle, CheckCircle2 } from 'lucide-react';
import { loginUser, registerUser } from '../api';

export default function AuthModal({
  tenants,
  onClose,
  onAuthSuccess,
}) {
  const [mode, setMode] = useState('login'); // 'login' or 'register'

  // Login form state
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  // Register form state
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regMobile, setRegMobile] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regOrgType, setRegOrgType] = useState('existing'); // 'existing' or 'new'
  const [regOrgId, setRegOrgId] = useState(tenants?.[0]?.id || 1);
  const [regNewOrgName, setRegNewOrgName] = useState('');

  const [isLoading, setIsLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');
    setIsLoading(true);

    try {
      const res = await loginUser(loginEmail.trim(), loginPassword);
      setSuccessMsg('Logged in successfully!');
      setTimeout(() => {
        onAuthSuccess(res.user);
        onClose();
      }, 500);
    } catch (err) {
      setErrorMsg(err.message || 'Login failed. Please verify credentials.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    setErrorMsg('');
    setSuccessMsg('');

    if (regPassword.length < 8 || !/\d/.test(regPassword) || !/[a-zA-Z]/.test(regPassword)) {
      setErrorMsg('Password must be at least 8 characters long and contain both letters and numbers.');
      return;
    }

    setIsLoading(true);
    try {
      const payload = {
        name: regName.trim(),
        email: regEmail.trim(),
        mobile: regMobile.trim(),
        password: regPassword,
        organization_id: regOrgType === 'existing' ? Number(regOrgId) : null,
        new_org_name: regOrgType === 'new' ? regNewOrgName.trim() : null,
        role: 'staff',
      };

      const res = await registerUser(payload);
      setSuccessMsg('Account created successfully!');
      setTimeout(() => {
        onAuthSuccess(res.user);
        onClose();
      }, 600);
    } catch (err) {
      setErrorMsg(err.message || 'Registration failed.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#16243F]/50 backdrop-blur-sm animate-float-in">
      <div className="bg-white border border-[#D9DDE2] rounded-2xl max-w-md w-full shadow-2xl overflow-hidden flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-5 border-b border-[#D9DDE2] bg-[#F5F6F3]">
          <div>
            <h3 className="font-serif text-lg font-bold text-[#16243F]">
              {mode === 'login' ? 'Staff Authentication' : 'Create Staff Account'}
            </h3>
            <p className="text-[11px] text-[#5B6573]">
              {mode === 'login'
                ? 'Sign in to access your organization portal'
                : 'Register to manage facility requests'}
            </p>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded-full flex items-center justify-center text-[#5B6573] hover:text-[#16243F] hover:bg-white transition-colors"
          >
            <X size={16} />
          </button>
        </div>

        {/* Tab Switcher */}
        <div className="flex border-b border-[#D9DDE2] text-xs font-semibold">
          <button
            type="button"
            onClick={() => {
              setMode('login');
              setErrorMsg('');
            }}
            className={`flex-1 py-3 text-center transition-colors cursor-pointer ${
              mode === 'login'
                ? 'text-[#C77F1F] border-b-2 border-[#C77F1F] bg-white'
                : 'text-[#5B6573] hover:text-[#16243F] bg-[#F5F6F3]/50'
            }`}
          >
            Sign In
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('register');
              setErrorMsg('');
            }}
            className={`flex-1 py-3 text-center transition-colors cursor-pointer ${
              mode === 'register'
                ? 'text-[#C77F1F] border-b-2 border-[#C77F1F] bg-white'
                : 'text-[#5B6573] hover:text-[#16243F] bg-[#F5F6F3]/50'
            }`}
          >
            Create Account
          </button>
        </div>

        {/* Form Body */}
        <div className="p-6">
          {errorMsg && (
            <div className="mb-4 bg-[#E8A33D]/12 border border-[#E8A33D]/30 text-[#16243F] text-xs p-3 rounded-lg flex items-start gap-2">
              <AlertCircle size={15} className="text-[#C77F1F] shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {successMsg && (
            <div className="mb-4 bg-[#1F7A5C]/12 border border-[#1F7A5C]/30 text-[#1F7A5C] text-xs p-3 rounded-lg flex items-center gap-2 font-medium">
              <CheckCircle2 size={16} />
              <span>{successMsg}</span>
            </div>
          )}

          {mode === 'login' ? (
            /* Login Form */
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Email Address
                </label>
                <div className="relative">
                  <Mail size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5B6573]" />
                  <input
                    type="email"
                    required
                    placeholder="admin@homedesk.com"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Password
                </label>
                <div className="relative">
                  <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5B6573]" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-[#16243F] hover:bg-[#2B3A55] text-white text-xs font-bold py-2.5 rounded-lg transition-colors shadow-sm disabled:opacity-50 cursor-pointer"
              >
                {isLoading ? 'Verifying...' : 'Sign In'}
              </button>

              <div className="text-center text-[11px] text-[#5B6573] pt-2">
                <span>Demo accounts: </span>
                <span className="font-mono text-[#16243F]">admin@homedesk.com</span>
                <span> (pass: </span>
                <span className="font-mono text-[#16243F]">Password123!</span>
                <span>)</span>
              </div>
            </form>
          ) : (
            /* Registration Form */
            <form onSubmit={handleRegister} className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Full Name *
                </label>
                <div className="relative">
                  <User size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5B6573]" />
                  <input
                    type="text"
                    required
                    placeholder="Ananya Verma"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-[#16243F] mb-1">
                    Email *
                  </label>
                  <input
                    type="email"
                    required
                    placeholder="user@org.com"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
                <div>
                  <label className="block text-xs font-medium text-[#16243F] mb-1">
                    Mobile *
                  </label>
                  <input
                    type="tel"
                    required
                    maxLength={10}
                    placeholder="9820011223"
                    value={regMobile}
                    onChange={(e) => setRegMobile(e.target.value.replace(/\D/g, ''))}
                    className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg font-mono focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Password (&ge;8 chars, letter + number) *
                </label>
                <div className="relative">
                  <Lock size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#5B6573]" />
                  <input
                    type="password"
                    required
                    placeholder="••••••••"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    className="w-full text-xs pl-9 pr-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Organization Membership
                </label>
                <div className="flex gap-4 text-xs mb-2">
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="orgType"
                      checked={regOrgType === 'existing'}
                      onChange={() => setRegOrgType('existing')}
                      className="text-[#E8A33D] focus:ring-0"
                    />
                    <span>Existing Tenant</span>
                  </label>
                  <label className="flex items-center gap-1.5 cursor-pointer">
                    <input
                      type="radio"
                      name="orgType"
                      checked={regOrgType === 'new'}
                      onChange={() => setRegOrgType('new')}
                      className="text-[#E8A33D] focus:ring-0"
                    />
                    <span>Create New Tenant</span>
                  </label>
                </div>

                {regOrgType === 'existing' ? (
                  <select
                    value={regOrgId}
                    onChange={(e) => setRegOrgId(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                  >
                    {tenants?.map((t) => (
                      <option key={t.id} value={t.id}>
                        {t.name}
                      </option>
                    ))}
                  </select>
                ) : (
                  <input
                    type="text"
                    required
                    placeholder="e.g. Apex Facilities Inc"
                    value={regNewOrgName}
                    onChange={(e) => setRegNewOrgName(e.target.value)}
                    className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                  />
                )}
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-[#16243F] hover:bg-[#2B3A55] text-white text-xs font-bold py-2.5 rounded-lg transition-colors shadow-sm disabled:opacity-50 cursor-pointer mt-2"
              >
                {isLoading ? 'Creating Account...' : 'Complete Registration'}
              </button>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
