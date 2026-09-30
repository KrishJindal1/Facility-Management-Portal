import React, { useState } from 'react';
import { X, CheckCircle, AlertCircle, ChefHat, Car, Shield } from 'lucide-react';
import { submitLead } from '../api';

const SERVICE_ICONS = {
  Cook: ChefHat,
  Driver: Car,
  'Security Guard': Shield,
};

export default function ServiceModal({
  serviceName,
  currentTenant,
  onClose,
  onRequirementSubmitted,
}) {
  const Icon = SERVICE_ICONS[serviceName] || ChefHat;

  // Form State
  const [formData, setFormData] = useState({
    Name: '',
    Mobile: '',
    Email: '',
    City: 'Mumbai',
    Budget: '15000',
    Pincode: '',
    // Cook specifics
    CuisineType: 'North Indian',
    MealsPerDay: '2',
    DietaryPreference: 'Both',
    // Driver specifics
    VehicleType: 'Sedan',
    Transmission: 'Automatic',
    DutyHours: '10 Hours',
    LicenseRequired: 'Commercial',
    // Security specifics
    Shift: 'Day Shift (12 hrs)',
    PremisesType: 'Gated Community',
    Experience: 'Standard (1-2 yrs)',
    // Additional notes
    Notes: '',
  });

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');
  const [successLead, setSuccessLead] = useState(null);

  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setErrorMsg('');

    // Client-side quick validations
    if (!formData.Name.trim()) {
      setErrorMsg('Full Name is required.');
      return;
    }
    if (!/^\d{10}$/.test(formData.Mobile.trim())) {
      setErrorMsg('Mobile number must be exactly 10 digits.');
      return;
    }
    if (!formData.Email.includes('@') || !formData.Email.includes('.')) {
      setErrorMsg('Please enter a valid email address.');
      return;
    }
    const numBudget = Number(formData.Budget);
    if (isNaN(numBudget) || numBudget <= 0) {
      setErrorMsg('Budget must be a positive number.');
      return;
    }

    setIsSubmitting(true);
    try {
      const orgId = currentTenant ? currentTenant.id : 1;

      // Construct lead submission payload
      const payloadData = {
        Name: formData.Name.trim(),
        Mobile: formData.Mobile.trim(),
        Email: formData.Email.trim(),
        City: formData.City,
        Budget: numBudget,
        Pincode: formData.Pincode.trim(),
        'Additional Notes': formData.Notes.trim(),
      };

      if (serviceName === 'Cook') {
        payloadData['Cuisine Type'] = formData.CuisineType;
        payloadData['Meals Per Day'] = Number(formData.MealsPerDay);
        payloadData['Dietary Preference'] = formData.DietaryPreference;
      } else if (serviceName === 'Driver') {
        payloadData['Vehicle Type'] = formData.VehicleType;
        payloadData['Transmission'] = formData.Transmission;
        payloadData['Duty Hours'] = formData.DutyHours;
        payloadData['License Required'] = formData.LicenseRequired;
      } else if (serviceName === 'Security Guard') {
        payloadData['Day/Night Shift'] = formData.Shift;
        payloadData['Residential/Commercial'] = formData.PremisesType;
        payloadData['Experience Level'] = formData.Experience;
      }

      const res = await submitLead(serviceName, payloadData, orgId);
      setSuccessLead(res.lead);

      if (onRequirementSubmitted) {
        onRequirementSubmitted({
          lead_id: res.lead['Lead ID'],
          mobile: formData.Mobile.trim(),
          service: serviceName,
          details: res.lead,
        });
      }
    } catch (err) {
      setErrorMsg(err.message || 'Failed to submit requirement. Please check fields.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-[#16243F]/50 backdrop-blur-sm animate-float-in">
      <div className="bg-white border border-[#D9DDE2] rounded-2xl max-w-xl w-full max-h-[90vh] overflow-y-auto shadow-2xl flex flex-col">
        {/* Modal Header */}
        <div className="flex items-center justify-between p-6 border-b border-[#D9DDE2] sticky top-0 bg-white z-10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[#E8A33D]/15 flex items-center justify-center text-[#C77F1F]">
              <Icon size={22} />
            </div>
            <div>
              <h2 className="font-serif text-xl font-bold text-[#16243F]">
                Hire a {serviceName}
              </h2>
              <div className="text-xs text-[#5B6573]">
                Tenant context: <b>{currentTenant?.name || 'HomeDesk Primary'}</b>
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-8 h-8 rounded-full flex items-center justify-center text-[#5B6573] hover:text-[#16243F] hover:bg-[#F5F6F3] transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {successLead ? (
            /* Success Confirmation State */
            <div className="text-center py-6">
              <div className="w-14 h-14 bg-[#1F7A5C]/12 text-[#1F7A5C] rounded-full flex items-center justify-center mx-auto mb-4">
                <CheckCircle size={32} />
              </div>
              <h3 className="font-serif text-2xl font-bold text-[#16243F] mb-1">
                Requirement Submitted!
              </h3>
              <p className="text-xs text-[#5B6573] mb-4">
                Your request has been recorded into the facility management database.
              </p>

              <div className="inline-block bg-[#F5F6F3] border border-[#D9DDE2] rounded-xl px-5 py-3 mb-6">
                <div className="text-[11px] uppercase tracking-wider text-[#5B6573] font-semibold">
                  Assigned Lead ID
                </div>
                <div className="font-mono text-2xl font-bold text-[#16243F]">
                  {successLead['Lead ID']}
                </div>
              </div>

              <div>
                <button
                  onClick={onClose}
                  className="bg-[#16243F] hover:bg-[#2B3A55] text-white text-xs font-semibold px-6 py-2.5 rounded-lg transition-colors"
                >
                  Return to Portal
                </button>
              </div>
            </div>
          ) : (
            /* Requirement Submission Form */
            <form onSubmit={handleSubmit} className="space-y-4">
              {errorMsg && (
                <div className="bg-[#E8A33D]/12 border border-[#E8A33D]/30 text-[#16243F] text-xs p-3 rounded-lg flex items-start gap-2">
                  <AlertCircle size={16} className="text-[#C77F1F] shrink-0 mt-0.5" />
                  <span>{errorMsg}</span>
                </div>
              )}

              {/* Section 1: Contact Details */}
              <div>
                <h4 className="text-xs font-bold text-[#C77F1F] uppercase tracking-wider mb-2">
                  Contact &amp; Location
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      Full Name *
                    </label>
                    <input
                      type="text"
                      name="Name"
                      required
                      placeholder="e.g. Ananya Sharma"
                      value={formData.Name}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      Mobile Number (10 Digits) *
                    </label>
                    <input
                      type="tel"
                      name="Mobile"
                      required
                      maxLength={10}
                      placeholder="e.g. 9820011223"
                      value={formData.Mobile}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg font-mono focus:outline-none focus:border-[#E8A33D]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      Email Address *
                    </label>
                    <input
                      type="email"
                      name="Email"
                      required
                      placeholder="name@example.com"
                      value={formData.Email}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      City *
                    </label>
                    <select
                      name="City"
                      value={formData.City}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                    >
                      <option>Mumbai</option>
                      <option>Pune</option>
                      <option>Delhi NCR</option>
                      <option>Bangalore</option>
                      <option>Chennai</option>
                      <option>Hyderabad</option>
                      <option>Kolkata</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      Monthly Budget (₹) *
                    </label>
                    <input
                      type="number"
                      name="Budget"
                      required
                      min={5000}
                      step={500}
                      value={formData.Budget}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-medium text-[#16243F] mb-1">
                      Pincode (Optional)
                    </label>
                    <input
                      type="text"
                      name="Pincode"
                      maxLength={6}
                      placeholder="e.g. 400001"
                      value={formData.Pincode}
                      onChange={handleChange}
                      className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                    />
                  </div>
                </div>
              </div>

              {/* Section 2: Service Specific Requirements */}
              <div className="pt-2 border-t border-[#D9DDE2]">
                <h4 className="text-xs font-bold text-[#C77F1F] uppercase tracking-wider mb-2">
                  {serviceName} Specifications
                </h4>

                {serviceName === 'Cook' && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Cuisine Preference
                      </label>
                      <select
                        name="CuisineType"
                        value={formData.CuisineType}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>North Indian</option>
                        <option>South Indian</option>
                        <option>Continental &amp; Italian</option>
                        <option>Chinese / Pan-Asian</option>
                        <option>Satvik / Jain Cuisine</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Meals Per Day
                      </label>
                      <select
                        name="MealsPerDay"
                        value={formData.MealsPerDay}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option value="1">1 Meal (Lunch or Dinner)</option>
                        <option value="2">2 Meals (Lunch &amp; Dinner)</option>
                        <option value="3">3 Meals (Breakfast, Lunch, Dinner)</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Dietary Preference
                      </label>
                      <select
                        name="DietaryPreference"
                        value={formData.DietaryPreference}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Both Veg &amp; Non-Veg</option>
                        <option>Strictly Vegetarian</option>
                      </select>
                    </div>
                  </div>
                )}

                {serviceName === 'Driver' && (
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Primary Vehicle Type
                      </label>
                      <select
                        name="VehicleType"
                        value={formData.VehicleType}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Hatchback / Compact</option>
                        <option>Sedan</option>
                        <option>SUV / MUV</option>
                        <option>Luxury Sedan</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Transmission
                      </label>
                      <select
                        name="Transmission"
                        value={formData.Transmission}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Automatic</option>
                        <option>Manual</option>
                        <option>Both Expert</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Daily Duty Hours
                      </label>
                      <select
                        name="DutyHours"
                        value={formData.DutyHours}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>8 Hours / Day</option>
                        <option>10 Hours / Day</option>
                        <option>12 Hours / Day</option>
                        <option>24 Hours Live-In</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        License Requirement
                      </label>
                      <select
                        name="LicenseRequired"
                        value={formData.LicenseRequired}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Commercial Yellow Badge</option>
                        <option>Private LMV</option>
                      </select>
                    </div>
                  </div>
                )}

                {serviceName === 'Security Guard' && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Shift Timings
                      </label>
                      <select
                        name="Shift"
                        value={formData.Shift}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Day Shift (12 hrs)</option>
                        <option>Night Shift (12 hrs)</option>
                        <option>24/7 Rotational</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Premises Type
                      </label>
                      <select
                        name="PremisesType"
                        value={formData.PremisesType}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Gated Community</option>
                        <option>Independent Villa</option>
                        <option>Commercial Office</option>
                      </select>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-[#16243F] mb-1">
                        Security Experience
                      </label>
                      <select
                        name="Experience"
                        value={formData.Experience}
                        onChange={handleChange}
                        className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg bg-white focus:outline-none focus:border-[#E8A33D]"
                      >
                        <option>Standard (1-2 yrs)</option>
                        <option>Senior (3+ yrs)</option>
                        <option>Ex-Serviceman / Armed</option>
                      </select>
                    </div>
                  </div>
                )}
              </div>

              {/* Additional Notes */}
              <div>
                <label className="block text-xs font-medium text-[#16243F] mb-1">
                  Additional Notes or Instructions
                </label>
                <textarea
                  name="Notes"
                  rows={2}
                  placeholder="Any specific requests, family preferences, or duty times..."
                  value={formData.Notes}
                  onChange={handleChange}
                  className="w-full text-xs px-3 py-2 border border-[#D9DDE2] rounded-lg focus:outline-none focus:border-[#E8A33D]"
                />
              </div>

              {/* Submit Button */}
              <div className="pt-2">
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full bg-[#16243F] hover:bg-[#2B3A55] text-white text-xs font-bold py-3 px-4 rounded-xl transition-all shadow-md disabled:opacity-50 cursor-pointer flex items-center justify-center gap-2"
                >
                  {isSubmitting ? 'Recording Requirement...' : 'Submit Request & Generate Lead ID'}
                </button>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );
}
