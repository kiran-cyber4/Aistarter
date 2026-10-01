// Tool declarations passed to Gemini, and the local functions that fulfill them.

const declarations = [
  {
    name: 'calculate',
    description: 'Evaluate a basic arithmetic expression, e.g. "12 * (3 + 4)".',
    parameters: {
      type: 'object',
      properties: {
        expression: {
          type: 'string',
          description: 'An arithmetic expression using numbers and + - * / ( ).',
        },
      },
      required: ['expression'],
    },
  },
  {
    name: 'get_current_time',
    description: 'Get the current date and time, optionally in a given IANA timezone.',
    parameters: {
      type: 'object',
      properties: {
        timezone: {
          type: 'string',
          description: 'IANA timezone name, e.g. "America/New_York". Defaults to UTC.',
        },
      },
    },
  },
];

function calculate({ expression }) {
  if (typeof expression !== 'string' || !/^[\d\s+\-*/().]+$/.test(expression)) {
    return { error: 'Expression contains unsupported characters.' };
  }
  try {
    // Safe because the expression is restricted to digits/operators/parens above.
    const result = Function(`"use strict"; return (${expression});`)();
    return { expression, result };
  } catch (err) {
    return { error: `Could not evaluate expression: ${err.message}` };
  }
}

function get_current_time({ timezone } = {}) {
  const now = new Date();
  try {
    return {
      timezone: timezone || 'UTC',
      datetime: now.toLocaleString('en-US', { timeZone: timezone || 'UTC' }),
      iso: now.toISOString(),
    };
  } catch (err) {
    return { error: `Unknown timezone "${timezone}".` };
  }
}

const implementations = { calculate, get_current_time };

async function callTool(name, args) {
  const fn = implementations[name];
  if (!fn) {
    return { error: `Unknown tool "${name}".` };
  }
  return fn(args || {});
}

module.exports = { declarations, callTool };
