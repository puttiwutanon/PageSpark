// styles/homeScreenStyles.js

import { StyleSheet } from 'react-native';

export const homeScreenStyle = StyleSheet.create({
  homeContainer: {
    flex: 1,
    experimental_backgroundImage: 'linear-gradient(360deg, #c9befc, #c6cdfc, #e2ddfd, #ece8fd)',
    paddingHorizontal: 20,
  },
  welcomeContainer: {
    marginTop: '15%',
    marginBottom: 24,
  },
  welcomeText: {
    fontSize: 24,
    color: '#1e293b',
  },
  subText: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 4,
  },
  routeToFunctionContainer: {
    flexDirection: 'row',
    gap: 12,
    marginBottom: 24,
  },
  routeToFunction: {
    flex: 1,
    backgroundColor: 'rgba(128, 128, 128, 0.27)',
    paddingVertical: 20,
    paddingHorizontal: 16,
    borderRadius: 16,
    alignItems: 'center',
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.05)',
  },
  recentActivityContainer: {
    flex: 1,
    backgroundColor: 'rgba(255,255,255,0.3)',
    borderRadius: 16,
    padding: 16,
    marginBottom: 150,
  },
  recentActivityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  recentHeaderTitle: {
    fontSize: 16,
    color: '#1e293b',
  },
  seeAllText: {
    fontSize: 13,
    color: '#818cf8',
    fontWeight: '500',
  },
  recentList: {
    paddingBottom: 8,
  },
  recentItem: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(255,255,255,0.6)',
    borderRadius: 12,
    padding: 12,
    marginBottom: 8,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.5)',
  },
  recentIcon: {
    width: 40,
    height: 40,
    borderRadius: 10,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  recentInfo: {
    flex: 1,
  },
  recentTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#1e293b',
  },
  recentSubtitle: {
    fontSize: 12,
    color: '#94a3b8',
    marginTop: 2,
  },
  recentRight: {
    alignItems: 'flex-end',
    gap: 4,
  },
  recentTime: {
    fontSize: 11,
    color: '#94a3b8',
  },
  recentLoading: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 30,
  },
  recentEmpty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 30,
    gap: 8,
  },
  recentEmptyText: {
    fontSize: 14,
    color: '#64748b',
    marginTop: 4,
  },
  recentEmptySubtext: {
    fontSize: 12,
    color: '#94a3b8',
  },
});