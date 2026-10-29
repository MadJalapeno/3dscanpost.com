// Single source for the visible FAQ section and the FAQPage JSON-LD.
module.exports = [
  {
    q: "What size parts can you scan?",
    a: "We can handle parts from small components (100mm x 100mm x 100mm) up to approximately half the size of a car. If you're unsure whether your part is too large, send us photos and we'll let you know."
  },
  {
    q: "What materials work best?",
    a: "Matte, non-reflective surfaces scan best. Shiny metal, transparent, or very dark black parts may require special preparation (like temporary coating spray). We'll advise you after reviewing your photos."
  },
  {
    q: "What if I can't ship it?",
    a: "We can arrange that you come to our facility (Seacoast, NH), or we can travel to you (travel time max 1hr)."
  },
  {
    q: "Do you offer CAD conversion or reverse engineering?",
    a: "CAD conversion requires understanding design intent, which varies by application - without knowing that the best we can do is recreate your part in Solidworks and give you a STEP file suitable for manufacturing. Price will depend on part geometry and will be discussed before work starts."
  },
  {
    q: "What if my part gets damaged in shipping?",
    a: "We handle all parts with care, but shipping carries inherent risks. We strongly recommend you purchase shipping insurance for valuable or irreplaceable items. You are responsible for properly packaging your part and insuring shipments both ways. Include a return shipping label in the package when you send your part."
  },
  {
    q: "Do I need a 3D scan for a flat part?",
    a: "Not always. For gaskets, brackets and other mostly flat parts, you can often trace an outline from a photo with a free-to-try tool like ShapeScan, which exports SVG, DXF and simple extruded STL files to about ±1mm. A 3D scan is the better choice when the part has real depth, curves or fine detail, or when you need tighter accuracy (our laser mode is ±0.2mm).",
    link: { href: "https://shapescan.pt/", text: "Visit ShapeScan" }
  },
  {
    q: "Are the scan files ready to 3D print?",
    a: "The scan files we provide are high-quality meshes, but they may require some cleanup or modification depending on your intended use. Most 3D printing slicers can import STL files directly, though you may need to repair or optimize the mesh for your specific application."
  },
  {
    q: "Do you accept parts from outside the US?",
    a: "Yes, we scan parts from anywhere in the world. Include a return shipping label in the package as usual. International customers are responsible for shipping, insurance and any customs duties or taxes in both directions, and should pay by PayPal (Venmo is US-only)."
  },
  {
    q: "What payment methods do you accept?",
    a: "We accept Venmo and PayPal. You pay after you've approved the scan screenshots."
  }
];
