"use client";
/**
 * FILE: AlchemyFumes.tsx
 * PURPOSE: CSS-only animated gas/fume clouds that float behind the jar.
 *          Overlay this BELOW AlchemyJar3D using absolute positioning.
 * USED BY: page.tsx (homepage hero)
 * USES: none (pure CSS animations)
 */
import React from "react";

// ──────────────────────────────────────────────
// EXPORT: Animated Gas Fumes (CSS only)
// ──────────────────────────────────────────────
export default function AlchemyFumes() {
  return (
    <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
      <div className="relative w-full max-w-[600px] aspect-square flex items-center justify-center">
        {/* Violet gas cloud - left side */}
        <div
          className="absolute rounded-full"
          style={{
            width: "70%", height: "55%",
            left: "-5%", top: "15%",
            background: "radial-gradient(ellipse, rgba(139,92,246,0.55) 0%, rgba(139,92,246,0.15) 50%, transparent 70%)",
            filter: "blur(45px)",
            animation: "gasViolet 8s ease-in-out infinite",
          }}
        />

        {/* Second violet wisp */}
        <div
          className="absolute rounded-full"
          style={{
            width: "45%", height: "40%",
            left: "10%", top: "45%",
            background: "radial-gradient(ellipse, rgba(124,58,237,0.45) 0%, transparent 65%)",
            filter: "blur(40px)",
            animation: "gasViolet 6s ease-in-out infinite",
            animationDelay: "2s",
          }}
        />

        {/* Blue gas cloud - right side */}
        <div
          className="absolute rounded-full"
          style={{
            width: "65%", height: "50%",
            right: "-5%", top: "20%",
            background: "radial-gradient(ellipse, rgba(59,130,246,0.5) 0%, rgba(59,130,246,0.15) 50%, transparent 70%)",
            filter: "blur(45px)",
            animation: "gasBlue 9s ease-in-out infinite",
            animationDelay: "1s",
          }}
        />

        {/* Second blue wisp */}
        <div
          className="absolute rounded-full"
          style={{
            width: "40%", height: "35%",
            right: "15%", top: "45%",
            background: "radial-gradient(ellipse, rgba(96,165,250,0.4) 0%, transparent 60%)",
            filter: "blur(35px)",
            animation: "gasBlue 7s ease-in-out infinite",
            animationDelay: "3s",
          }}
        />

        {/* Center purple mist (core) */}
        <div
          className="absolute rounded-full"
          style={{
            width: "55%", height: "55%",
            background: "radial-gradient(circle, rgba(109,40,217,0.6) 0%, rgba(76,29,149,0.2) 50%, transparent 75%)",
            filter: "blur(40px)",
            animation: "gasPulse 5s ease-in-out infinite",
            animationDelay: "1.5s",
          }}
        />
      </div>

      {/* Keyframe animations */}
      <style jsx>{`
        @keyframes gasViolet {
          0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.7;
          }
          25% {
            transform: translate(20px, -15px) scale(1.1);
            opacity: 0.9;
          }
          50% {
            transform: translate(-10px, 10px) scale(1.15);
            opacity: 0.6;
          }
          75% {
            transform: translate(15px, 5px) scale(0.95);
            opacity: 0.8;
          }
        }
        @keyframes gasBlue {
          0%, 100% {
            transform: translate(0, 0) scale(1);
            opacity: 0.6;
          }
          30% {
            transform: translate(-18px, -12px) scale(1.12);
            opacity: 0.85;
          }
          60% {
            transform: translate(12px, 8px) scale(0.9);
            opacity: 0.5;
          }
        }
        @keyframes gasPulse {
          0%, 100% {
            transform: translate(-50%, -50%) scale(1);
            opacity: 0.5;
          }
          50% {
            transform: translate(-50%, -50%) scale(1.25);
            opacity: 0.8;
          }
        }
      `}</style>
    </div>
  );
}
