/** A form or a review the site refuses, with every reason it gives. */
export class ValidationError extends Error {
  readonly problems: string[];

  constructor(problems: string[]) {
    super(problems.join("; "));
    this.name = "ValidationError";
    this.problems = problems;
  }
}
