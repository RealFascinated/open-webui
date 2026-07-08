export type ChatGreetingKey =
	| 'Hello, {{name}}'
	| 'Good morning, {{name}}'
	| 'Good afternoon, {{name}}'
	| 'Good evening, {{name}}'
	| 'Hey, {{name}}'
	| 'Hi, {{name}}'
	| 'Welcome back, {{name}}';

const TIME_GREETINGS: Record<'morning' | 'afternoon' | 'evening' | 'night', ChatGreetingKey> = {
	morning: 'Good morning, {{name}}',
	afternoon: 'Good afternoon, {{name}}',
	evening: 'Good evening, {{name}}',
	night: 'Good evening, {{name}}'
};

const RANDOM_GREETINGS: ChatGreetingKey[] = [
	'Hello, {{name}}',
	'Hey, {{name}}',
	'Hi, {{name}}',
	'Welcome back, {{name}}'
];

export const getTimeOfDay = (date = new Date()): keyof typeof TIME_GREETINGS => {
	const hour = date.getHours();

	if (hour >= 5 && hour < 12) return 'morning';
	if (hour >= 12 && hour < 17) return 'afternoon';
	if (hour >= 17 && hour < 22) return 'evening';
	return 'night';
};

export const getChatGreetingKey = (date = new Date()): ChatGreetingKey => {
	const timeGreeting = TIME_GREETINGS[getTimeOfDay(date)];
	const options = [timeGreeting, ...RANDOM_GREETINGS.filter((greeting) => greeting !== timeGreeting)];

	return options[Math.floor(Math.random() * options.length)];
};
