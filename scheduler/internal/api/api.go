package api

import (
	"context"

	servicespb "github.com/Vol-v/ai-assistant/protobufs/gen/go/apis/services"
)

type Scheduler struct {
	servicespb.UnimplementedSchedulerServiceServer

	// scheduler scheduler.Scheduler
}

func (s *Scheduler) CancelTask(ctx context.Context, in *servicespb.CancelTaskRequest) (*servicespb.CancelTaskResponse, error) {
	return nil, nil
}
func (s *Scheduler) GetTask(ctx context.Context, in *servicespb.GetTaskRequest) (*servicespb.GetTaskResponse, error) {
	return nil, nil
}
func (s *Scheduler) ListTasks(ctx context.Context, in *servicespb.ListTasksRequest) (*servicespb.ListTasksResponse, error) {
	return nil, nil
}
func (s *Scheduler) ScheduleTask(ctx context.Context, in *servicespb.ScheduleTaskRequest) (*servicespb.ScheduleTaskResponse, error) {
	return nil, nil
}
