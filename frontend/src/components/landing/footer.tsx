import { Globe, Link as LinkIcon, Video } from "lucide-react";
import { Logo } from "@/components/brand/logo";

const cols = [
  { title: "Product", links: ["Features", "Demo", "Documentation"] },
  { title: "Resources", links: ["Research", "Blog", "Support"] },
  { title: "Company", links: ["About", "Contact", "Careers"] },
];

export function Footer() {
  return (
    <footer className="border-t" style={{ borderColor: "var(--border)" }}>
      <div className="mx-auto grid max-w-[1360px] gap-10 px-6 py-12 md:grid-cols-[1.4fr_1fr_1fr_1fr_1.2fr]">
        <div>
          <Logo />
          <p className="mt-3 text-sm" style={{ color: "var(--text-muted)" }}>From Network Data to Security Intelligence</p>
        </div>
        {cols.map((c) => (
          <div key={c.title}>
            <h4 className="text-sm font-bold" style={{ color: "var(--text)" }}>{c.title}</h4>
            <ul className="mt-3 space-y-2 text-sm" style={{ color: "var(--text-muted)" }}>
              {c.links.map((l) => <li key={l}><a href="#">{l}</a></li>)}
            </ul>
          </div>
        ))}
        <div>
          <h4 className="text-sm font-bold" style={{ color: "var(--text)" }}>Connect With Us</h4>
          <div className="mt-3 flex gap-2">
            {[<Globe key="g" size={16} />, <LinkIcon key="l" size={16} />, <Video key="y" size={16} />].map((icon, i) => (
              <a key={i} href="#" aria-label="Social link" className="grid h-9 w-9 place-items-center rounded-[10px] border" style={{ borderColor: "var(--border)", color: "var(--text-muted)" }}>
                {icon}
              </a>
            ))}
          </div>
        </div>
      </div>
      <div className="mx-auto flex max-w-[1360px] items-center justify-between border-t px-6 py-5 text-xs" style={{ borderColor: "var(--border)", color: "var(--text-subtle)" }}>
        <span>© 2026 THREATWEAVE. All rights reserved.</span>
        <span>Built for a Safer Digital World.</span>
      </div>
    </footer>
  );
}
