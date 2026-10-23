import { useEffect, useMemo, useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { PageHeader } from "../components/layout/PageHeader";
import { paletteFor, RobotAvatar, variantForName } from "../components/character/RobotAvatar";
import { Banner } from "../components/ui/Banner";
import { Button } from "../components/ui/Button";
import { ErrorState } from "../components/ui/ErrorState";
import { LoadingBlock } from "../components/ui/LoadingBlock";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { ApiError } from "../services/client";
import { createBattle, fetchCharacters } from "../services/battles";
import type { BattleStyle, Character, Intensity, PlaybackMode } from "../types/api";

const TOPIC_IDEAS = [
  "who has the best antenna",
  "pizza toppings tier list",
  "is cereal a soup",
  "best robot superpower",
  "the correct way to fold socks",
];

const STYLES: { value: BattleStyle; label: string; hint: string }[] = [
  { value: "rap", label: "Rap", hint: "Rhymes and punchlines" },
  { value: "roast", label: "Roast", hint: "Friendly teasing" },
  { value: "debate", label: "Debate", hint: "Sharp arguments" },
];

const INTENSITIES: { value: Intensity; label: string }[] = [
  { value: "playful", label: "Playful" },
  { value: "spicy", label: "Spicy" },
  { value: "fiery", label: "Fiery" },
];

export function BattleSetupPage() {
  useDocumentTitle("New battle");
  const navigate = useNavigate();

  const [characters, setCharacters] = useState<Character[]>([]);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [fighterA, setFighterA] = useState<string>("");
  const [fighterB, setFighterB] = useState<string>("");
  const [topic, setTopic] = useState("");
  const [style, setStyle] = useState<BattleStyle>("rap");
  const [intensity, setIntensity] = useState<Intensity>("playful");
  const [rounds, setRounds] = useState(3);
  const [playback, setPlayback] = useState<PlaybackMode>("manual");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const load = useMemo(
    () => () => {
      setLoading(true);
      fetchCharacters()
        .then((data) => {
          setCharacters(data);
          setFighterA((current) => current || data[0]?.id || "");
          setFighterB((current) => current || data[1]?.id || "");
          setLoadError(null);
        })
        .catch((err: unknown) => {
          setLoadError(err instanceof ApiError ? err.message : "Could not load the robots.");
        })
        .finally(() => setLoading(false));
    },
    [],
  );

  useEffect(() => {
    load();
  }, [load]);

  const selectedA = characters.find((c) => c.id === fighterA);
  const selectedB = characters.find((c) => c.id === fighterB);

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setFormError(null);

    if (!fighterA || !fighterB) {
      setFormError("Pick two robots.");
      return;
    }
    if (fighterA === fighterB) {
      setFormError("Pick two different robots.");
      return;
    }
    if (topic.trim().length < 3) {
      setFormError("Give the battle a topic of at least 3 characters.");
      return;
    }

    setSubmitting(true);
    try {
      const battle = await createBattle({
        fighter_a_id: fighterA,
        fighter_b_id: fighterB,
        topic: topic.trim(),
        style,
        intensity,
        round_count: rounds,
        playback_mode: playback,
      });
      navigate(`/battle/${battle.id}`);
    } catch (err) {
      const apiError = err instanceof ApiError ? err : null;
      setFormError(
        apiError?.fields[0]?.message ?? apiError?.message ?? "The battle could not be created.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <AppShell narrow>
      <PageHeader
        title="Set up a battle"
        subtitle="Pick two robots, give them something to argue about, and press start."
      />

      {loading ? <LoadingBlock label="Waking up the robots…" /> : null}
      {loadError ? <ErrorState message={loadError} onRetry={load} /> : null}

      {!loading && !loadError ? (
        <form onSubmit={handleSubmit} className="grid gap-5">
          <fieldset className="bv-card px-5 py-4">
            <legend className="px-1 text-sm font-bold uppercase tracking-wide text-[var(--color-muted)]">
              Fighters
            </legend>
            <div className="mt-2 grid gap-4 sm:grid-cols-2">
              <FighterPicker
                label="Robot A"
                characters={characters}
                value={fighterA}
                disabledId={fighterB}
                onChange={setFighterA}
              />
              <FighterPicker
                label="Robot B"
                characters={characters}
                value={fighterB}
                disabledId={fighterA}
                onChange={setFighterB}
              />
            </div>
          </fieldset>

          <div className="bv-card grid gap-4 px-5 py-4">
            <div>
              <label htmlFor="topic" className="text-sm font-bold">
                Battle topic
              </label>
              <input
                id="topic"
                value={topic}
                onChange={(event) => setTopic(event.target.value)}
                maxLength={120}
                placeholder="e.g. who has the best antenna"
                className="mt-1 w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2.5 text-base outline-none focus:border-[var(--color-primary)]"
                required
              />
              <div className="mt-2 flex flex-wrap gap-1.5">
                {TOPIC_IDEAS.map((idea) => (
                  <button
                    key={idea}
                    type="button"
                    onClick={() => setTopic(idea)}
                    className="bv-transition rounded-full border border-[var(--color-line)] bg-white px-3 py-1 text-xs text-[var(--color-muted)] hover:border-[var(--color-primary)] hover:text-[var(--color-primary-ink)]"
                  >
                    {idea}
                  </button>
                ))}
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <span className="text-sm font-bold">Tone</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {STYLES.map((option) => (
                    <Choice
                      key={option.value}
                      selected={style === option.value}
                      onClick={() => setStyle(option.value)}
                      label={option.label}
                      hint={option.hint}
                    />
                  ))}
                </div>
              </div>
              <div>
                <span className="text-sm font-bold">Intensity</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  {INTENSITIES.map((option) => (
                    <Choice
                      key={option.value}
                      selected={intensity === option.value}
                      onClick={() => setIntensity(option.value)}
                      label={option.label}
                    />
                  ))}
                </div>
              </div>
            </div>

            <div className="grid gap-4 sm:grid-cols-2">
              <div>
                <label htmlFor="rounds" className="text-sm font-bold">
                  Rounds: {rounds} <span className="font-normal text-[var(--color-muted)]">({rounds * 2} verses)</span>
                </label>
                <input
                  id="rounds"
                  type="range"
                  min={1}
                  max={5}
                  step={1}
                  value={rounds}
                  onChange={(event) => setRounds(Number(event.target.value))}
                  className="mt-2 w-full accent-[var(--color-primary)]"
                />
              </div>
              <div>
                <span className="text-sm font-bold">Playback</span>
                <div className="mt-1 flex flex-wrap gap-2">
                  <Choice
                    selected={playback === "manual"}
                    onClick={() => setPlayback("manual")}
                    label="Manual"
                    hint="You press next"
                  />
                  <Choice
                    selected={playback === "auto"}
                    onClick={() => setPlayback("auto")}
                    label="Auto"
                    hint="Generates every turn"
                  />
                </div>
              </div>
            </div>
          </div>

          {formError ? (
            <Banner tone="danger" role="alert">
              {formError}
            </Banner>
          ) : null}

          <div className="flex flex-wrap items-center gap-3">
            <Button type="submit" variant="primary" size="lg" busy={submitting}>
              Start battle
            </Button>
            <Button type="button" variant="ghost" onClick={() => navigate("/")}>
              Cancel
            </Button>
            {selectedA && selectedB ? (
              <p className="text-sm text-[var(--color-muted)]">
                {selectedA.name} vs {selectedB.name}
              </p>
            ) : null}
          </div>
        </form>
      ) : null}
    </AppShell>
  );
}

function Choice({
  selected,
  onClick,
  label,
  hint,
}: {
  selected: boolean;
  onClick: () => void;
  label: string;
  hint?: string;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={selected}
      title={hint}
      className={`bv-transition min-h-[44px] rounded-2xl border px-4 py-2 text-sm font-semibold ${
        selected
          ? "border-[var(--color-primary)] bg-[#f4f1ff] text-[var(--color-primary-ink)]"
          : "border-[var(--color-line)] bg-white text-[var(--color-ink)] hover:border-[#d9d1c8]"
      }`}
    >
      {label}
    </button>
  );
}

function FighterPicker({
  label,
  characters,
  value,
  disabledId,
  onChange,
}: {
  label: string;
  characters: Character[];
  value: string;
  disabledId: string;
  onChange: (id: string) => void;
}) {
  return (
    <div>
      <span className="text-xs font-bold uppercase tracking-wide text-[var(--color-muted)]">
        {label}
      </span>
      <div className="mt-1 grid gap-2">
        {characters.map((character) => {
          const palette = paletteFor(character.accent);
          const selected = value === character.id;
          const disabled = disabledId === character.id;
          return (
            <button
              key={character.id}
              type="button"
              onClick={() => onChange(character.id)}
              disabled={disabled}
              aria-pressed={selected}
              className={`bv-transition flex items-center gap-3 rounded-2xl border px-3 py-2 text-left disabled:opacity-40 ${
                selected ? "bg-white shadow-[var(--shadow-soft)]" : "bg-white/60 hover:bg-white"
              }`}
              style={{ borderColor: selected ? palette.body : "var(--color-line)" }}
            >
              <RobotAvatar
                accent={character.accent}
                variant={variantForName(character.name)}
                size={48}
              />
              <span className="min-w-0">
                <span className="block text-sm font-bold">{character.name}</span>
                <span className="block text-xs text-[var(--color-muted)]">
                  {character.tagline}
                </span>
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}