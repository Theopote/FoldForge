export type SampleCase = {
  id: string;
  title: string;
  tag: string;
  difficulty: "Easy" | "Standard" | "Advanced";
  summary: string;
  bestFor: string;
  settings: string;
  color: string;
  samplePath?: string;
  sampleFileName?: string;
  prompt?: string;
};

export const SAMPLE_CASES: SampleCase[] = [
  {
    id: "starter-box",
    title: "Starter Gift Box",
    tag: "First build",
    difficulty: "Easy",
    summary: "A clean cube-based model for checking print scale, tabs, folds, and page layout.",
    bestFor: "First-time users, classroom demos, printer calibration",
    settings: "A4, Easy, 80-100 mm height",
    color: "from-emerald-100 via-white to-teal-100",
    samplePath: "/samples/box.stl",
    sampleFileName: "box.stl",
    prompt: "A simple low poly gift box with broad faces for beginner papercraft",
  },
  {
    id: "pyramid-marker",
    title: "Pyramid Table Marker",
    tag: "Fast fold",
    difficulty: "Easy",
    summary: "A small pyramid form that produces few parts and makes mountain folds obvious.",
    bestFor: "Name cards, tabletop markers, quick workshop examples",
    settings: "A4, Easy, 70-90 mm height",
    color: "from-amber-100 via-white to-orange-100",
    samplePath: "/samples/pyramid.stl",
    sampleFileName: "pyramid.stl",
    prompt: "A simple geometric pyramid table marker for printable papercraft",
  },
  {
    id: "low-poly-pet",
    title: "Low Poly Pet",
    tag: "Character",
    difficulty: "Standard",
    summary: "A friendly animal form with enough facets to test seam placement and numbering.",
    bestFor: "Kids projects, decorative toys, character style tests",
    settings: "A4, Standard, 100-140 mm height",
    color: "from-sky-100 via-white to-cyan-100",
    prompt: "A cute low poly cat sitting upright, designed for beginner papercraft",
  },
  {
    id: "robot-mascot",
    title: "Robot Mascot",
    tag: "Toy",
    difficulty: "Standard",
    summary: "A blocky mascot with simple limbs, good for checking part labels and assembly order.",
    bestFor: "Desk toys, maker events, product mascots",
    settings: "A4, Standard, 120 mm height",
    color: "from-violet-100 via-white to-indigo-100",
    prompt: "A cute chibi robot toy with a square head and simple low poly body",
  },
  {
    id: "castle-tower",
    title: "Castle Tower",
    tag: "Display",
    difficulty: "Advanced",
    summary: "A taller architectural model that stresses layout, page count, and craftability warnings.",
    bestFor: "Display pieces, architecture tests, advanced builders",
    settings: "A3, Advanced, 160-220 mm height",
    color: "from-rose-100 via-white to-pink-100",
    prompt: "A geometric fantasy castle tower with crenellations for papercraft",
  },
];

export const LOADABLE_SAMPLE_CASES = SAMPLE_CASES.filter(
  (sample): sample is SampleCase & { samplePath: string; sampleFileName: string } =>
    Boolean(sample.samplePath && sample.sampleFileName),
);

export const TEXT_PROMPT_CASES = SAMPLE_CASES.filter((sample) => sample.prompt);
