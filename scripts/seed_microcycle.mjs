import { initializeApp, cert } from 'firebase-admin/app';
import { getFirestore } from 'firebase-admin/firestore';
import { readFileSync } from 'fs';
import { resolve } from 'path';

const KEY_PATH = process.argv[2] || resolve(process.env.HOME, '.config/wilo-service-account.json');
const serviceAccount = JSON.parse(readFileSync(KEY_PATH, 'utf8'));

initializeApp({ credential: cert(serviceAccount) });
const db = getFirestore('wilo');

// Week of Sept 21 2026 (Sunday)
const WEEK_OF = '2026-09-21';

const SLED = {
  id: 'blk_sled',
  name: 'Sled',
  notes: '6 lengths forward, 2 reverse. Every session.',
  exercises: [
    {
      id: 'ex_sled_forward',
      name: 'Sled drag — forward',
      sets: 6,
      cue: '3 plates. One length per set.',
      start_weight_lbs: 135
    },
    {
      id: 'ex_sled_reverse',
      name: 'Sled drag — reverse',
      sets: 2,
      cue: '3 plates.',
      start_weight_lbs: 135
    }
  ]
};

const microcycle = {
  weekOf: WEEK_OF,
  createdAt: new Date().toISOString(),
  programs: [
    // Monday — Session A (upper/shoulder)
    {
      day: 1,
      id: 'sess_a_upper',
      name: 'Session A — Shoulder + Upper',
      blocks: [
        {
          id: 'blk_upper',
          name: 'Upper',
          notes: 'Decline curl first — it loads the scapula and makes bench feel better.',
          exercises: [
            {
              id: 'ex_decline_curl',
              name: 'Decline biceps curl',
              sets: 3,
              cue: 'Full stretch at bottom. Sets up scapula for bench.',
              start_weight_lbs: 20
            },
            {
              id: 'ex_bench',
              name: 'Bench press',
              sets: 3,
              cue: 'Upper back already loaded from curls. Use it.',
              start_weight_lbs: 135
            },
            {
              id: 'ex_barbell_ohp',
              name: 'Barbell overhead press',
              sets: 3,
              cue: 'Full lockout. Elbows forward at bottom.',
              start_weight_lbs: 65
            },
            {
              id: 'ex_kneeling_landmine',
              name: 'Kneeling landmine press',
              sets: 3,
              cue: 'One side at a time. Tall kneeling, press on diagonal.',
              start_weight_lbs: 45
            },
            {
              id: 'ex_lateral_raise',
              name: 'Lateral raise',
              sets: 3,
              cue: 'Light. Full range — from hip to ear height. No swinging.',
              start_weight_lbs: 10
            }
          ]
        },
        SLED
      ]
    },

    // Wednesday — Session B (half, morning)
    {
      day: 3,
      id: 'sess_b_half_upper',
      name: 'Session B — Half Upper (morning)',
      blocks: [
        {
          id: 'blk_upper_b',
          name: 'Upper — condensed',
          notes: 'Half session. Quality over quantity.',
          exercises: [
            {
              id: 'ex_barbell_ohp_b',
              name: 'Barbell overhead press',
              sets: 3,
              cue: 'Full lockout.',
              start_weight_lbs: 65
            },
            {
              id: 'ex_kneeling_landmine_b',
              name: 'Kneeling landmine press',
              sets: 2,
              cue: 'One side at a time.',
              start_weight_lbs: 45
            },
            {
              id: 'ex_lateral_raise_b',
              name: 'Lateral raise',
              sets: 2,
              cue: 'Light. Full range.',
              start_weight_lbs: 10
            }
          ]
        },
        SLED
      ]
    },

    // Thursday — Legs
    {
      day: 4,
      id: 'sess_legs',
      name: 'Legs',
      blocks: [
        {
          id: 'blk_legs',
          name: 'Legs',
          notes: 'Crane airplanes are hard — they should be.',
          exercises: [
            {
              id: 'ex_single_leg_press',
              name: 'Single leg press',
              sets: 3,
              cue: 'Weak side first. Full range.',
              start_weight_lbs: 90
            },
            {
              id: 'ex_step_up',
              name: 'Step up',
              sets: 3,
              cue: 'Drive through heel. Getting better — keep going.',
              start_weight_lbs: 25
            },
            {
              id: 'ex_crane_airplane',
              name: 'Crane airplanes',
              sets: 3,
              cue: 'Control the descent. Both legs to start.',
              start_weight_lbs: 0
            },
            {
              id: 'ex_lateral_raise_c',
              name: 'Lateral raise',
              sets: 2,
              cue: 'Light. Full range.',
              start_weight_lbs: 10
            }
          ]
        },
        SLED
      ]
    },

    // Friday — Deadlifts
    {
      day: 5,
      id: 'sess_deadlift',
      name: 'Deadlifts',
      blocks: [
        {
          id: 'blk_dl',
          name: 'Deadlift',
          notes: 'Heavy first while fresh. Speed work after.',
          exercises: [
            {
              id: 'ex_deadlift_heavy',
              name: 'Deadlift — heavy',
              sets: 5,
              cue: '405. 1-2 reps per set. Full reset between reps.',
              start_weight_lbs: 405
            },
            {
              id: 'ex_deadlift_speed',
              name: 'Deadlift — speed/form',
              sets: 4,
              cue: '315. Fast off the floor. Bar stays close.',
              start_weight_lbs: 315
            },
            {
              id: 'ex_lateral_raise_d',
              name: 'Lateral raise',
              sets: 2,
              cue: 'Light. Full range.',
              start_weight_lbs: 10
            }
          ]
        },
        SLED
      ]
    }
  ]
};

async function seed() {
  const docId = `microcycle-${WEEK_OF}`;
  await db.collection('microcycles').doc(docId).set(microcycle);
  console.log(`✓ microcycle written: ${docId}`);
  console.log(`  ${microcycle.programs.length} programs:`);
  microcycle.programs.forEach(p => {
    const days = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
    console.log(`  ${days[p.day]} — ${p.name}`);
  });
}

seed().catch(err => { console.error('Failed:', err.message); process.exit(1); });
