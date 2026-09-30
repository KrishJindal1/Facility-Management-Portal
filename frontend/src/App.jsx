import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import Hero from './components/Hero';
import ServiceCards from './components/ServiceCards';
import ServiceModal from './components/ServiceModal';
import AuthModal from './components/AuthModal';
import ChatbotWidget from './components/ChatbotWidget';
import Footer from './components/Footer';
import { fetchTenants } from './api';

export default function App() {
  const [tenants, setTenants] = useState([
    { id: 1, name: 'HomeDesk Primary', slug: 'homedesk' },
    { id: 2, name: 'Acme Facilities', slug: 'acme' },
  ]);
  const [currentTenant, setCurrentTenant] = useState({
    id: 1,
    name: 'HomeDesk Primary',
    slug: 'homedesk',
  });

  const [currentUser, setCurrentUser] = useState(null);
  const [activeRequest, setActiveRequest] = useState(null);
  const [selectedService, setSelectedService] = useState(null);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);

  // Initialize from localStorage and fetch tenants
  useEffect(() => {
    // 1. Restore Auth state
    const savedUser = localStorage.getItem('homedesk_user');
    if (savedUser) {
      try {
        const parsed = JSON.parse(savedUser);
        setCurrentUser(parsed);
      } catch (e) {
        localStorage.removeItem('homedesk_user');
      }
    }

    // 2. Restore Tracked Request
    const savedRequest = localStorage.getItem('homedesk_request');
    if (savedRequest) {
      try {
        const parsed = JSON.parse(savedRequest);
        setActiveRequest(parsed);
      } catch (e) {
        localStorage.removeItem('homedesk_request');
      }
    }

    // 3. Fetch Tenants from Backend API
    fetchTenants()
      .then((data) => {
        if (Array.isArray(data) && data.length > 0) {
          setTenants(data);

          // Check URL query param: ?tenant=acme
          const urlParams = new URLSearchParams(window.location.search);
          const tenantSlug = urlParams.get('tenant') || urlParams.get('org');

          if (tenantSlug) {
            const matched = data.find((t) => t.slug === tenantSlug.toLowerCase());
            if (matched) {
              setCurrentTenant(matched);
              return;
            }
          }

          // If user is already logged in, lock tenant
          if (savedUser) {
            try {
              const u = JSON.parse(savedUser);
              const userOrg = data.find((t) => t.id === u.organization_id);
              if (userOrg) {
                setCurrentTenant(userOrg);
                return;
              }
            } catch (e) {}
          }

          setCurrentTenant(data[0]);
        }
      })
      .catch((err) => {
        console.warn('Could not load tenants from API, using defaults:', err);
      });
  }, []);

  const handleSelectTenant = (tenantId) => {
    if (currentUser) {
      // Authenticated user cannot switch away from their bound organization
      return;
    }
    const target = tenants.find((t) => t.id === tenantId);
    if (target) {
      setCurrentTenant(target);
      const url = new URL(window.location);
      url.searchParams.set('tenant', target.slug);
      window.history.pushState({}, '', url);
    }
  };

  const handleAuthSuccess = (user) => {
    setCurrentUser(user);
    localStorage.setItem('homedesk_user', JSON.stringify(user));

    // Lock tenant to user's organization
    const userOrg = tenants.find((t) => t.id === user.organization_id);
    if (userOrg) {
      setCurrentTenant(userOrg);
    } else {
      setCurrentTenant({
        id: user.organization_id,
        name: user.organization_name || 'Organization',
        slug: user.organization_slug || 'org',
      });
    }
  };

  const handleLogout = () => {
    setCurrentUser(null);
    localStorage.removeItem('homedesk_user');
    // Reset to primary tenant
    if (tenants.length > 0) {
      setCurrentTenant(tenants[0]);
      const url = new URL(window.location);
      url.searchParams.delete('tenant');
      window.history.pushState({}, '', url);
    }
  };

  const handleSaveRequest = (req) => {
    setActiveRequest(req);
    localStorage.setItem('homedesk_request', JSON.stringify(req));
  };

  const handleClearRequest = () => {
    setActiveRequest(null);
    localStorage.removeItem('homedesk_request');
  };

  return (
    <div className="min-h-screen bg-[#F5F6F3] text-[#16243F]">
      <div className="max-w-[1100px] mx-auto px-4 sm:px-6 pt-6 sm:pt-8 pb-16">
        {/* Brand Header */}
        <Header
          tenants={tenants}
          currentTenant={currentTenant}
          onSelectTenant={handleSelectTenant}
          currentUser={currentUser}
          onOpenAuth={() => setIsAuthModalOpen(true)}
          onLogout={handleLogout}
        />

        {/* Hero Section & Token Card */}
        <Hero
          currentTenant={currentTenant}
          activeRequest={activeRequest}
          onSaveRequest={handleSaveRequest}
          onClearRequest={handleClearRequest}
        />

        {/* Service Cards (Cook, Driver, Security Guard) */}
        <ServiceCards onSelectService={(serviceKey) => setSelectedService(serviceKey)} />

        {/* Footer with Excel Export and Copyright */}
        <Footer currentTenant={currentTenant} />

        {/* Service Requirement Modal */}
        {selectedService && (
          <ServiceModal
            serviceName={selectedService}
            currentTenant={currentTenant}
            onClose={() => setSelectedService(null)}
            onRequirementSubmitted={handleSaveRequest}
          />
        )}

        {/* Auth Modal (Sign In / Register) */}
        {isAuthModalOpen && (
          <AuthModal
            tenants={tenants}
            onClose={() => setIsAuthModalOpen(false)}
            onAuthSuccess={handleAuthSuccess}
          />
        )}

        {/* Floating Conversational AI Chatbot Widget */}
        <ChatbotWidget />
      </div>
    </div>
  );
}
