import { timeZoneLabel } from '../../dates'

export type TimeZoneGroup = { region: string; zones: { value: string; label: string }[] }

/** The browser's IANA timezones, grouped by region ("Africa", "America", …) for the picker. */
export function timeZoneGroups(): TimeZoneGroup[] {
  const groups = new Map<string, TimeZoneGroup['zones']>()
  for (const zone of Intl.supportedValuesOf('timeZone')) {
    const region = zone.includes('/') ? zone.slice(0, zone.indexOf('/')) : zone
    const zones = groups.get(region) ?? []
    zones.push({ value: zone, label: timeZoneLabel(zone) })
    groups.set(region, zones)
  }
  return [...groups].map(([region, zones]) => ({ region, zones }))
}
