import React, { useEffect } from 'react';
import { Link, NavLink, useLocation } from 'react-router-dom';
import { ArrowRight, ArrowUpRight, Smartphone, Layers3, Box, Menu, X, Check, ChevronRight } from 'lucide-react';
import { BrandLogo } from '../../components/brand/BrandLogo';
import './website.css';
const pages = [
    { path: '/website', name: 'Overview' },
    { path: '/website/platform', name: 'Platform' },
    { path: '/website/approach', name: 'Our approach' },
    { path: '/website/guide', name: 'Capture guide' },
];
const steps = [
    ['01', 'Set up your space', 'Create a project, add a room, and start a capture session from the platform.'],
    ['02', 'Record on your phone', 'Pair with the session QR code. Move through the room slowly, keeping surfaces in view.'],
    ['03', 'Follow reconstruction', 'Track upload verification, depth estimation, geometry, and quality checks in one place.'],
    ['04', 'Review the result', 'Open the viewer when processing and quality validation have completed successfully.'],
];
const workflow = [
    ['Capture & upload', 'A session connects the recording to its project. Chunked uploads can resume, and file checksums are verified before processing.'],
    ['Depth & camera tracking', 'Metric depth estimation and camera-pose estimation provide the observations used to reconstruct visible surfaces.'],
    ['Geometry & appearance', 'Native Open3D fuses observations into a mesh. Image projection creates textures for the reconstructed geometry.'],
    ['Validation & delivery', 'Measured checks evaluate the result. A rejected scan remains visible in the pipeline with its failure details.'],
];
function Heading({ eyebrow, title, children }: {
    eyebrow: string;
    title: string;
    children: React.ReactNode;
}) {
    return <header className="site-page-heading"><span className="site-eyebrow">{eyebrow}</span><h1>{title}</h1><p>{children}</p></header>;
}
function Overview() {
    return <>
    <section className="site-hero">
      <div className="site-hero-copy"><span className="site-eyebrow">VĀSTU / NAMMA SPACE</span><h1>Every space has<br />a story.<br /><em>Start with yours.</em></h1><p>Bring room recordings, reconstruction, and spatial review into one shared workspace. From your phone to a space your team can explore.</p><div className="site-actions"><Link className="site-button" to="/login">Open workspace <ArrowUpRight size={17}/></Link><Link className="site-text-link" to="/website/platform">Explore the platform <ArrowRight size={16}/></Link></div><div className="site-hero-note"><Smartphone size={17}/><span>Capture on mobile. Review together on the web.</span></div></div>
      <div className="site-project-preview">
        <div className="site-preview-bar"><span><span className="site-dot"/> SPACE PREVIEW</span><span>01 / INTERIOR</span></div>
        <div className="site-room-photo"><img src="/models/01_keyframes/frame_02.png" alt="An interior frame from the sample room recording"/><span className="site-photo-label">Sample capture · Interior study</span><div className="site-photo-corner">V / 01</div></div>
        <div className="site-preview-caption"><div><span className="site-eyebrow">A NEW PERSPECTIVE</span><h3>A familiar room.<br />A shared point of reference.</h3></div><Link to="/website/approach" aria-label="Read about our approach"><ArrowUpRight size={24}/></Link></div>
      </div>
    </section>
    <section className="site-summary-strip"><span>ONE CONNECTED WORKFLOW</span><div><Smartphone size={18}/> Record</div><ChevronRight size={15}/><div><Layers3 size={18}/> Reconstruct</div><ChevronRight size={15}/><div><Box size={18}/> Review</div></section>
    <section className="site-section"><div className="site-section-heading"><div><span className="site-eyebrow">BUILT AROUND THE PROJECT</span><h2>Less scattered.<br />More connected.</h2></div><p>A recording belongs to a room. A room belongs to a project. Keep the context with the work, from the first capture to the final review.</p></div><div className="site-feature-grid">{[['01', 'A place for every space', 'Organize projects, floors, and rooms so your team knows what is being captured.'], ['02', 'Progress you can follow', 'See which processing stage is running and inspect the reason when a scan needs attention.'], ['03', 'A result you can review', 'Explore accepted reconstruction outputs through the project’s web viewer.']].map(([n, t, d]) => <article key={n}><span className="site-number">{n}</span><h3>{t}</h3><p>{d}</p></article>)}</div></section>
    <section className="site-guide-callout"><div><span className="site-eyebrow">BEFORE YOUR FIRST RECORDING</span><h2>A better capture starts<br />with a little preparation.</h2><p>Good light, steady movement, and overlapping views make a difference.</p><Link className="site-text-link" to="/website/guide">Read the capture guide <ArrowRight size={17}/></Link></div><div className="site-callout-note"><span>FIELD NOTE / 01</span><Smartphone size={42} strokeWidth={1}/><p>Walk through the space.<br />Give the camera a changing viewpoint.</p><small>Movement provides evidence for geometry.</small></div></section>
  </>;
}
function Platform() {
    return <><Heading eyebrow="THE PLATFORM" title="Your project. In perspective.">A shared workspace for the people recording a space and the people reviewing it.</Heading><section className="site-workspace"><div className="site-workspace-sidebar"><BrandLogo size="sm" theme="light"/><span className="site-eyebrow">WORKSPACE PREVIEW</span>{['Overview', 'Projects', 'Capture sessions', 'Pipeline', 'Assets'].map((v, i) => <div key={v} className={i === 1 ? 'selected' : ''}>{v}</div>)}</div><div className="site-workspace-main"><span className="site-eyebrow">PROJECT / EXAMPLE</span><h2>Interior survey</h2><p>Keep every recording connected to the right room.</p><div className="site-example-room"><img src="/models/01_keyframes/frame_02.png" alt="Sample interior recording frame"/><div><span className="site-eyebrow">GROUND FLOOR</span><h3>Main room</h3><span className="site-outline-badge">Illustrative project</span></div></div><div className="site-example-row"><span>Capture session</span><span>Upload → Processing → Review</span></div><small>This is a product illustration, not a live project status.</small></div></section><section className="site-section"><div className="site-section-heading"><h2>From fieldwork<br />to shared review.</h2><p>One project holds the context at every step.</p></div><div className="site-feature-grid">{[[Smartphone, 'Capture sessions', 'Create a room-specific session and pair the mobile app with a server-issued QR code.'], [Layers3, 'Pipeline monitoring', 'Inspect processing stages, job logs, and validation outcomes from the project dashboard.'], [Box, 'Spatial review', 'Open available viewer outputs and review them alongside the project’s capture history.']].map(([Icon, title, copy]) => { const I = Icon as typeof Box; return <article key={String(title)}><I size={25} strokeWidth={1.4}/><h3>{String(title)}</h3><p>{String(copy)}</p></article>; })}</div></section></>;
}
function Approach() {
    return <><Heading eyebrow="OUR APPROACH" title="A space built from observations.">Reconstruction starts with what the camera sees. Each step turns those observations into geometry that can be inspected.</Heading><section className="site-method-layout"><aside><span className="site-eyebrow">RECORDING → RECONSTRUCTION</span><h2>Evidence at<br />every step.</h2><p>The workflow combines existing depth models and native geometry tools with project management, upload verification, and processing orchestration.</p><Link className="site-text-link" to="/website/guide">Capture better inputs <ArrowRight size={16}/></Link></aside><div className="site-method-list">{workflow.map(([t, d], i) => <article key={t}><span className="site-number">0{i + 1}</span><div><h3>{t}</h3><p>{d}</p></div></article>)}</div></section><section className="site-honesty"><span className="site-eyebrow">UNDERSTANDING THE RESULT</span><h2>A digital reconstruction<br />is a measured interpretation.</h2><div><p>Lighting, reflective surfaces, occlusion, and camera movement affect the result. Surfaces that were never observed may remain incomplete.</p><p>Quality checks help identify problems; they do not establish survey-grade accuracy. Verify critical dimensions with independent measurements.</p></div></section></>;
}
function Guide() {
    return <><Heading eyebrow="CAPTURE GUIDE" title="A little care. A clearer space.">Prepare the room, move steadily, and give the camera overlapping views. Use this guide for your first capture session.</Heading><section className="site-guide-layout"><aside><span className="site-eyebrow">BEFORE YOU START</span><h3>Ready to record?</h3>{['Use even lighting', 'Clear the walking path', 'Keep the lens clean', 'Check battery and storage'].map(t => <p className="site-check" key={t}><Check size={16}/>{t}</p>)}<Link className="site-button" to="/login">Open workspace <ArrowUpRight size={16}/></Link></aside><div className="site-method-list">{steps.map(([n, t, d]) => <article key={n}><span className="site-number">{n}</span><div><h3>{t}</h3><p>{d}</p>{n === '02' && <div className="site-inline-note">Walk slowly through the room rather than only turning in one spot. Keep adjacent views overlapping and include walls, corners, floor, and ceiling where safe.</div>}</div></article>)}</div></section><section className="site-section site-faq"><span className="site-eyebrow">WHEN A CAPTURE NEEDS ATTENTION</span><h2>A few useful answers.</h2>{[['The upload was interrupted. What next?', 'Keep the recording on your device and retry the upload. The upload workflow checks which chunks are still missing.'], ['Why is reconstruction taking time?', 'Depth estimation and geometry processing can take time, especially on a CPU. Follow the project pipeline and its logs to see the current stage.'], ['Why was the result rejected?', 'Open the scan’s pipeline details and inspect the failed quality checks. A retry helps transient errors; capture or geometry issues may need a different recording or processing changes.'], ['Can I use the result for precise measurements?', 'Independently verify dimensions before using them for construction or other accuracy-critical work.']].map(([q, a]) => <details key={q}><summary>{q}<span>+</span></summary><p>{a}</p></details>)}</section></>;
}
export const ProjectWebsitePage: React.FC = () => {
    const { pathname } = useLocation();
    const [menuOpen, setMenuOpen] = React.useState(false);
    const key = pathname.includes('platform') ? 'platform' : pathname.includes('approach') || pathname === '/about' ? 'approach' : pathname.includes('guide') ? 'guide' : 'overview';
    useEffect(() => { document.title = `VĀSTU — ${key === 'overview' ? 'Spaces, in perspective' : key === 'guide' ? 'Capture guide' : key === 'platform' ? 'The platform' : 'Our approach'}`; window.scrollTo(0, 0); setMenuOpen(false); }, [pathname, key]);
    return <div className="vastu-site"><a className="site-skip" href="#website-main">Skip to content</a><header className="site-header"><Link to="/website" aria-label="Vastu home"><BrandLogo size="md" theme="light"/></Link><nav aria-label="Website" className={menuOpen ? 'open' : ''}>{pages.map(p => <NavLink end key={p.path} to={p.path} className={({ isActive }) => isActive || (p.path === '/website' && key === 'overview') ? 'active' : ''}>{p.name}</NavLink>)}</nav><Link className="site-header-login" to="/login">Open workspace <ArrowUpRight size={15}/></Link><button className="site-menu" aria-label={menuOpen ? 'Close navigation' : 'Open navigation'} aria-expanded={menuOpen} onClick={() => setMenuOpen(!menuOpen)}>{menuOpen ? <X /> : <Menu />}</button></header><main id="website-main">{key === 'platform' ? <Platform /> : key === 'approach' ? <Approach /> : key === 'guide' ? <Guide /> : <Overview />}</main><footer className="site-footer"><div><BrandLogo size="sm" theme="light"/><p>Mapping spaces. Building digital twins.</p></div><div>{pages.map(p => <Link key={p.path} to={p.path}>{p.name}</Link>)}</div><span>VĀSTU / Namma Space<br />Spatial capture & reconstruction</span></footer></div>;
};
