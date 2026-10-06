import { Navbar } from "@/components/landing/navbar";
import { Hero } from "@/components/landing/hero";
import { HowItWorks } from "@/components/landing/how-it-works";
import { LiveDemo } from "@/components/landing/live-demo";
import { ProductDemo } from "@/components/landing/product-demo";
import { Capabilities } from "@/components/landing/capabilities";
import { MitreAI } from "@/components/landing/mitre-ai";
import { FinalCta } from "@/components/landing/final-cta";
import { Footer } from "@/components/landing/footer";

export default function Landing() {
  return (
    <main>
      <Navbar />
      <Hero />
      <HowItWorks />
      <LiveDemo />
      <ProductDemo />
      <Capabilities />
      <MitreAI />
      <FinalCta />
      <Footer />
    </main>
  );
}
