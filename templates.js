/**
 * WhatsApp Outreach Templates - Web Development Pitch
 * Specifically designed for businesses & property dealers who do NOT have a website.
 * 
 * Available Placeholders:
 *   {name}        - Business / Dealer Name
 *   {address}     - Locality / City
 *   {category}    - Category (e.g. Real estate consultant)
 *   {senderName}  - Your Name / Agency Signature
 */

const templates = [
  // Variation 1: Value & Local Google Presence Focus
  `Hi {name},

I came across your profile in {address} and was impressed by your presence in the local market.

I noticed that you don't currently have an official website listed for {name}. Nowadays, most property buyers and investors search Google before calling, and without a website, high-value inquiries often get lost to competitors.

We build modern, fast websites specifically for property consultants — featuring:
✅ Property & Plot listing showcase
✅ 1-Click direct WhatsApp lead buttons
✅ Google Search & Maps integration

Would you be open to seeing a quick, free sample design we can put together for {name}?

Best regards,
{senderName}`,

  // Variation 2: Direct Leads & Independence from Paid Portals
  `Hello {name},

Greetings! I noticed your business in {address}.

Are you currently relying mostly on paid portals (like 99acres/MagicBricks) or offline walk-ins for leads?

Having your own branded website for {name} helps you:
1. Capture direct buyer inquiries straight to your WhatsApp (0% commission)
2. Build trust with serious clients & NRI investors
3. Showcase your hot residential & commercial inventory 24/7

We create professional real estate websites quickly and very affordably.

Can I send you a quick 2-minute demo link to show how it would look?

Thanks,
{senderName}`,

  // Variation 3: Short, Direct & High-Converting
  `Hi {name},

Hope you are doing well! Reaching out regarding your business in {address}.

I checked online but couldn't find an official website for {name}. Having a dedicated website gives your clients instant trust and brings verified buyer calls directly from Google search.

We help local property dealers launch clean, mobile-friendly websites with instant WhatsApp inquiry buttons in just 48 hours.

Would you be open to checking out a free demo preview tailored for your business?

Best regards,
{senderName}`
];

/**
 * Returns a personalized web development outreach message.
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
  
  const cleanName = (lead.name || 'Sir/Madam').trim();
  const cleanAddress = (lead.address || 'your area')
    .split(',')
    .slice(-3, -1)
    .join(',')
    .trim() || lead.address || 'your area';

  text = text.replace(/{name}/g, cleanName);
  text = text.replace(/{address}/g, cleanAddress);
  text = text.replace(/{category}/g, lead.category || 'Business');
  text = text.replace(/{senderName}/g, senderName);

  return text;
}

module.exports = {
  templates,
  getPersonalizedMessage
};
