// Mirrors backend/app/services/modes.py so the UI describes what each mode really does.
export const MODES = {
  quick: {
    id: 'quick',
    label: 'Quick Research',
    blurb: '3 searches · up to 8 sources · concise report',
    detail: 'Fastest. Good for a first look.',
    eta: '≈ 30 – 60 s',
  },
  deep: {
    id: 'deep',
    label: 'Deep Research',
    blurb: '7 searches · up to 18 sources · detailed report',
    detail: 'Reads every source, then compares across them.',
    eta: '≈ 1 – 3 min',
  },
}

export const SUGGESTED_TOPICS = [
  'Current status of solid-state battery commercialization for electric vehicles',
  'What does recent evidence say about the health effects of intermittent fasting?',
  'How are governments regulating generative AI, and where do approaches differ?',
  'Pros and cons of small modular nuclear reactors for grid power',
  'What are the main causes and treatments of long COVID according to recent studies?',
  'Compare Rust and Go for building backend services',
]

// `from` = progress percentage (reported by the backend) at which the step becomes active.
export const PIPELINE_STEPS = [
  { label: 'Plan searches', from: 0 },
  { label: 'Search the web', from: 20 },
  { label: 'Collect sources', from: 45 },
  { label: 'Analyze evidence', from: 52 },
  { label: 'Check citations', from: 90 },
]

export const FOLLOW_UP_IDEAS = [
  'What are the biggest limitations of this research?',
  'Where do the sources disagree?',
  'Summarize this in three bullet points.',
]

// Home page: starters prefill the box with the start of a good research question; cards load a full example topic.
export const QUICK_STARTERS = [
  { label: 'Latest developments', icon: 'news', prefix: 'What are the latest developments in ' },
  { label: 'Pros and cons', icon: 'scale', prefix: 'What are the pros and cons of ' },
  { label: 'Compare options', icon: 'compare', prefix: 'Compare the main options for ' },
]

export const SUGGESTION_CARDS = [
  {
    tag: 'Energy', icon: 'battery', title: 'Solid-state batteries',
    desc: 'Where commercialization stands for electric vehicles.',
    topic: 'Current status of solid-state battery commercialization for electric vehicles',
  },
  {
    tag: 'Health', icon: 'heart', title: 'Intermittent fasting',
    desc: 'What recent evidence says about its health effects.',
    topic: 'What does recent evidence say about the health effects of intermittent fasting?',
  },
  {
    tag: 'Policy', icon: 'landmark', title: 'AI regulation',
    desc: 'How governments regulate generative AI, and where they differ.',
    topic: 'How are governments regulating generative AI, and where do approaches differ?',
  },
]
