// Plain static content, no fetch/RAG/chat here on purpose — see DECISIONS.md.
// A "FAQ chatbot" would read as exactly the "wrapped RAG chatbot" the
// hackathon brief says loses; a static reference page doesn't compete with
// the resolver as the app's actual differentiator. Facts below are drawn
// from the same corpus docs (backend/app/data/corpus/) that ground the
// tracker's explanations, so nothing here can contradict what a student sees
// on their own plan.

const FAQS: { q: string; a: string }[] = [
  {
    q: "Do I need a Social Security Number to open a US bank account?",
    a: "Usually not. Most banks — including school-partnered ones — accept a passport plus your I-20 (F-1) or DS-2019 (J-1) and proof of local address. An SSN is sometimes asked for later to unlock certain features, but it's not required just to open a basic checking account.",
  },
  {
    q: "Can I start an on-campus job before I have an SSN?",
    a: "Yes. You can begin working with an \"SSN applied for\" status while the application is processing — the SSN is required to get paid correctly long-term, not to start the job itself.",
  },
  {
    q: "What has to happen before I can apply for an SSN?",
    a: "You need a qualifying job offer (on-campus, or off-campus authorization like CPT/OPT) first — that's what lets your school's international office issue the eligibility documentation. Only with that documentation in hand can you apply at an SSA office.",
  },
  {
    q: "Why is one student blocked on their SSN and another isn't, even at the same school?",
    a: "It comes down to job-offer status. A student with no job offer can't even request the eligibility letter yet, so they're blocked earlier in the chain than a student who has an offer but just hasn't finished the paperwork — even though both currently \"don't have an SSN.\"",
  },
  {
    q: "How long does the physical SSN card take to arrive?",
    a: "Typically 2–4 weeks after your in-person SSA visit, assuming your paperwork (I-20/DS-2019, passport, visa, I-94, and your school's eligibility letter) is complete.",
  },
  {
    q: "I have no US credit history — how do I start building one?",
    a: "Two common starting points: a secured credit card (deposit-backed, easiest to qualify for with no credit history), or becoming an authorized user on a family member's or trusted friend's existing card.",
  },
];

export default function FaqsPage() {
  return (
    <main className="mx-auto w-full max-w-2xl flex-1 px-6 py-10">
      <h1 className="text-2xl font-semibold text-slate-900">FAQs</h1>
      <p className="mt-1 mb-6 text-sm text-slate-500">
        Common questions about the US financial-setup process in general — for how <em>your</em> situation
        specifically sequences, see the Tracker.
      </p>

      <div className="space-y-3">
        {FAQS.map((item) => (
          <details
            key={item.q}
            className="group rounded-2xl border border-blue-100 bg-white p-4 open:shadow-sm"
          >
            <summary className="cursor-pointer list-none font-medium text-slate-900 marker:content-none">
              <span className="mr-2 inline-block text-blue-700 transition-transform group-open:rotate-90">›</span>
              {item.q}
            </summary>
            <p className="mt-2 pl-5 text-sm leading-relaxed text-slate-600">{item.a}</p>
          </details>
        ))}
      </div>
    </main>
  );
}
