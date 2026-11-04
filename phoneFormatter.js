/**
 * Utility for formatting and validating phone numbers for WhatsApp.
 */

function formatWhatsAppNumber(rawPhone, defaultCountryCode = '91') {
  if (!rawPhone) return null;

  // Remove non-digit characters
  let digits = String(rawPhone).replace(/\D/g, '');

  // Strip leading 0s (common in Indian formats like 094165...)
  while (digits.startsWith('0')) {
    digits = digits.substring(1);
  }

  // If 10 digits (standard Indian mobile number without country code)
  if (digits.length === 10) {
    digits = defaultCountryCode + digits;
  }

  // Validate mobile number length: usually 11-13 digits with country code
  if (digits.length < 10 || digits.length > 15) {
    return null;
  }

  return {
    cleanNumber: digits,
    chatId: `${digits}@c.us`,
    display: `+${digits}`
  };
}

module.exports = {
  formatWhatsAppNumber
};
