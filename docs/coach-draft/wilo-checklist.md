# WILO coach: checklist to get new chats loading the skill

## Flows
- [x] User can't do the current exercise
- [x] Plan a Workout
- [ ] Onboarding a new User (Profile starts empty). Record manual transcripts first, then build the flow and checklist from them. If answers to the "like" and "wish I liked" lists are vague, default to pushups and say so.
- [ ] Pain and other exceptions
- [ ] Traces of every coaching conversation (for evals), and store what the Model learns about the User in the right place

## Open question
- [ ] If the Model offers suggestions and the User picks none, does the flow go to "Other exercises left in the Remaining Workout?" (my guess, not confirmed)

## Ship it
- [ ] Move the draft into wilo/coach.md in the repo
- [ ] Remove the smiley and dead hang canary lines, and the stale "don't tap Load" text
- [ ] Fix loading: claude.ai treated the method as a possible prompt injection when it came back from a tool. Decide how the connector tells Claude to call coaching_method first (connector instructions, a real skill, or both)
- [ ] Test in a fresh chat with a brand-new account
