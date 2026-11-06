/**
 * WhatsApp Outreach Templates - Conversational & Non-Salesy
 * Crafted specifically for real estate consultants & property dealers.
 * 
 * Key Principles:
 *  1. Short (under 4-5 lines) - Easy to read on a phone screen.
 *  2. Conversational & Humble - Does NOT sound like an agency sales pitch.
 *  3. Curious Question Hook - High reply rate ("Do you have a link or share on WhatsApp?").
 *  4. Low-Friction Ask - "Can I share a 1-minute demo link?"
 * 
 * Available Placeholders:
 *   {name}        - Clean Business / Dealer Name
 *   {address}     - Locality / City
 *   {category}    - Category (e.g. Real estate consultant)
 *   {senderName}  - Your Name / Signature
 */

const templates = [
  // Variation 1: Natural Hinglish (Highest reply rate in India - Friendly inquiry)
  `Namaste {name} ji,

Main {address} me aapka profile dekh raha tha.
Aapke paas available properties dekhne ke liye koi website link hai, ya fir aap inventory direct WhatsApp par hi share karte hain?

Actually humne property consultants ke liye ek simple 1-click WhatsApp showcase demo banaya hai. Agar aap kahen to 1 minute ka preview link share karun?

- {senderName}`,

  // Variation 2: Clean, Casual English (Curious & Natural)
  `Hi {name},

Came across your real estate business in {address}.

Quick question — do you have a website link to view your active properties, or do you share listings directly on WhatsApp?

I recently designed a simple mobile portfolio demo tailored for property consultants (with direct WhatsApp inquiry buttons). 

Would you be open to checking out a quick 1-minute demo link?

Best,
{senderName}`,

  // Variation 3: Short Helpful Observation (Hinglish/English mix)
  `Hello {name} ji,

I was looking up your property business in {address} on Google, but noticed you don't have an official website link attached.

We put together a clean 1-page mobile showcase demo made for property dealers so buyers can browse your hot listings and WhatsApp you directly.

Can I share a quick 1-minute preview link with you to see how it looks?

- {senderName}`
];

/**
 * Clean dealer name by stripping promotional suffixes like ': Property dealer in ...'
 */
function cleanDealerName(rawName) {
  if (!rawName) return 'Sir/Madam';
  let name = String(rawName).trim();
  // Strip common suffixes
  name = name.split(':')[0].split('|')[0].split('-')[0].trim();
  // Remove leading/trailing non-alphanumeric except spaces
  name = name.replace(/^[^a-zA-Z0-9\s]+|[^a-zA-Z0-9\s]+$/g, '').trim();
  return name || String(rawName).trim();
}

/**
 * Clean address to extract just the locality and city
 */
function cleanDealerAddress(rawAddress) {
  if (!rawAddress) return 'your area';
  const parts = String(rawAddress)
    .split(',')
    .map(p => p.trim())
    .filter(Boolean);

  if (parts.length === 0) return 'your area';

  // Filter out standalone pincodes (6 digits)
  const cleanParts = parts
    .map(p => p.replace(/\b\d{6}\b/g, '').trim())
    .filter(Boolean);

  if (cleanParts.length >= 2) {
    return cleanParts.slice(-2).join(', ');
  }
  return cleanParts[0] || parts[0] || 'your area';
}

/**
 * Returns a personalized, non-salesy outreach message.
 * @param {object} lead 
 * @param {number} [templateIndex]
 * @param {string} [senderName]
 * @returns {string}
 */
function getPersonalizedMessage(lead, templateIndex, senderName = 'Deepaktusir') {
  const index = typeof templateIndex === 'number' 
    ? templateIndex % templates.length 
    : Math.floor(Math.random() * templates.length);

  let text = templates[index];
  
  const cleanName = cleanDealerName(lead.name);
  const cleanAddress = cleanDealerAddress(lead.address);

  text = text.replace(/{name}/g, cleanName);
  text = text.replace(/{address}/g, cleanAddress);
  text = text.replace(/{category}/g, lead.category || 'Business');
  text = text.replace(/{senderName}/g, senderName);

  return text;
}

module.exports = {
  templates,
  cleanDealerName,
  cleanDealerAddress,
  getPersonalizedMessage
};
