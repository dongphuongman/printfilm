"use client";

import Link from "next/link";
import { ArrowRight, Construction, Sparkles } from "lucide-react";
import { useCurrentProject } from "@/components/shell/current-project";
import { PfMain, PfPageHead, PfPanel } from "@/components/shell/pf-layout";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useT } from "@/i18n/locale-provider";

export function PlaceholderPage({
  title,
  description,
}: {
  title: string;
  description: string;
}) {
  const { currentProject } = useCurrentProject();
  const t = useT();

  return (
    <PfMain>
      <PfPageHead title={title} description={description} />
      <PfPanel className="flex min-h-[420px] flex-col items-center justify-center text-center">
        <span className="grid size-14 place-items-center rounded-xl bg-[#b6ff00] text-[#111318]">
          <Construction className="size-6" />
        </span>
        <Badge className="mt-5 bg-[#efffc7] text-[#466400] hover:bg-[#efffc7]" variant="secondary">
          <Sparkles className="mr-1 size-3" />
          {t("shell.comingSoon")}
        </Badge>
        <h2 className="mt-4 text-2xl font-bold tracking-tight">{title}</h2>
        <p className="mt-3 max-w-xl text-sm leading-relaxed text-[var(--pf-muted)]">{description}</p>
        {currentProject && (
          <p className="mt-3 rounded-full border border-[#d7ed9d] bg-[#efffc7] px-3 py-1 text-xs text-[#466400]">
            {t("shell.currentProjectNamed", { name: currentProject.name })}
          </p>
        )}
        <div className="mt-8 flex flex-wrap justify-center gap-3">
          <Button asChild className="bg-[#b6ff00] font-semibold text-[#111318] hover:bg-[#a8f000]">
            <Link href="/creator">
              {t("shell.backToCreator")}
              <ArrowRight />
            </Link>
          </Button>
          <Button asChild variant="outline" className="bg-white">
            <Link href="/projects">{t("nav.projects")}</Link>
          </Button>
        </div>
      </PfPanel>
    </PfMain>
  );
}
